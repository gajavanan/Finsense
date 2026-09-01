from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from datetime import date, datetime
from app.core.security import get_current_user
from app.core.database import get_db
from app.models import User, Transaction, Notification, AgentInsight, Budget, SpendingAlert
from app.schemas.transaction import TransactionCreate, TransactionUpdate
from app.api.v1.ws import manager
import uuid

router = APIRouter()

def to_dict(o):
    d = {c.name: getattr(o,c.name) for c in o.__table__.columns}
    for k,v in list(d.items()):
        if hasattr(v,'isoformat'): d[k]=v.isoformat()
        elif str(type(v)).find('Decimal')!=-1: d[k]=float(v)
    # alias handling for frontend compat: expose both type and transaction_type
    if "transaction_type" in d and d.get("transaction_type"):
        d["transaction_type"] = d["transaction_type"]
        d["type"] = d["transaction_type"]
    elif d.get("type"):
        d["transaction_type"] = d["type"]
    # monthly_limit alias not here but for transaction we ensure type present
    return d

def normalize_transaction_type(payload: dict) -> str:
    # priority: transaction_type > type
    raw = payload.get("transaction_type") or payload.get("type")
    if not raw: raise HTTPException(400, "transaction_type (income/expense) is required")
    val = str(raw).lower().strip()
    if val not in ("income","expense","transfer"):
        # map transfer to expense/income? keep as is but spec says income/expense
        if val == "transfer": return "expense"  # fallback
        raise HTTPException(400, "transaction_type must be income or expense")
    if val == "transfer": val = "expense"
    return val

def check_budget_alerts(user_id: str, category: str, db: Session):
    """Check 75/90/100 thresholds after expense creation, avoid duplicate alerts for same threshold"""
    if not category: return
    now = datetime.utcnow()
    # find budgets matching this category for current month/year or global
    budgets = db.query(Budget).filter(Budget.user_id==user_id, Budget.category==category).all()
    if not budgets: return
    # calculate spent this month for category
    month_str = now.strftime("%Y-%m")
    # filter transactions for this month/category
    from sqlalchemy import func
    txs = db.query(Transaction).filter(
        Transaction.user_id==user_id,
        Transaction.category==category,
        Transaction.transaction_type=="expense"
    ).all()
    # filter by month in python for sqlite compatibility
    spent = 0
    for t in txs:
        try:
            if t.date and t.date.strftime("%Y-%m")==month_str:
                spent += float(t.amount)
        except: pass
    for b in budgets:
        # Use monthly_limit if set else amount
        limit_val = float(b.monthly_limit if b.monthly_limit is not None else b.amount)
        if limit_val == 0: continue
        pct = spent / limit_val * 100
        # determine threshold crossed
        threshold = None
        msg = None
        if pct >= 100:
            threshold = "100"
            msg = f"You have exceeded your {category} budget by ₹{round(spent - limit_val,2)}."
        elif pct >= 90:
            threshold = "90"
            msg = f"You have used 90% of your {category} budget."
        elif pct >= 75:
            threshold = "75"
            msg = f"You have used 75% of your {category} budget."
        else:
            continue
        # avoid duplicate alerts: check if alert already exists for this category+threshold this month
        existing = db.query(SpendingAlert).filter(
            SpendingAlert.user_id==user_id,
            SpendingAlert.category==category,
            SpendingAlert.alert_type==threshold,
            SpendingAlert.created_at >= datetime(now.year, now.month, 1)
        ).first()
        if existing:
            continue
        alert = SpendingAlert(
            user_id=user_id,
            alert_type=threshold,
            category=category,
            message=msg,
            amount=spent
        )
        db.add(alert)
        # also create notification for immediate UI
        notif = Notification(user_id=user_id, title="Budget Alert", message=msg, type="alert")
        db.add(notif)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"alert creation failed {e}")

@router.get("/transactions")
async def list_transactions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    search: Optional[str] = None,
    category: Optional[str] = None,
    type: Optional[str] = Query(None, alias="type"),
    transaction_type: Optional[str] = Query(None, alias="transaction_type"),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    page: int = 1,
    limit: int = 20,
    sort: str = "date",
    order: str = "desc"
):
    q = db.query(Transaction).filter(Transaction.user_id==user.id)
    # filter by transaction_type with alias support
    tt = transaction_type or type
    if tt:
        tt_norm = str(tt).lower()
        # filter where transaction_type or legacy type matches
        q = q.filter(or_(Transaction.transaction_type==tt_norm, Transaction.type==tt_norm))
    if category:
        q = q.filter(Transaction.category==category)
    if search:
        q = q.filter(or_(Transaction.description.ilike(f"%{search}%"), Transaction.merchant.ilike(f"%{search}%")))
    if date_from:
        q = q.filter(Transaction.date >= date_from)
    if date_to:
        q = q.filter(Transaction.date <= date_to)
    total = q.count()
    # guard sort column
    allowed_sort = ["date","amount","created_at","category"]
    if sort not in allowed_sort: sort = "date"
    col = getattr(Transaction, sort, Transaction.date)
    if order=="desc":
        q = q.order_by(col.desc())
    else:
        q = q.order_by(col.asc())
    items = q.offset((page-1)*limit).limit(limit).all()
    return {"data": [to_dict(x) for x in items], "count": total, "page": page, "limit": limit}

@router.post("/transactions")
async def create_transaction(payload: TransactionCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = payload.model_dump()
    # validate ownership via JWT already (user.id)
    tx_type = normalize_transaction_type(data)
    # sync both columns for backward compat
    data["transaction_type"] = tx_type
    data["type"] = tx_type
    # amount already validated >0 via pydantic
    if not data.get("category") or data["category"] in (None,""):
        try:
            from app.ml.predictors.categorizer import categorize_transaction
            cat_res = categorize_transaction(data.get("description",""), data.get("merchant"))
            data["category"] = cat_res.get("category","Other")
            data["confidence_score"] = cat_res.get("confidence",0)
        except Exception as e:
            print(f"categorize failed {e}")
            data["category"] = "Other"
            data["confidence_score"] = 0
    else:
        # user provided category - but still compute confidence as 1.0 manual
        data["confidence_score"] = 1.0
        # allow preset confidence 1.0
    # ensure source
    if not data.get("source"): data["source"]="manual"
    # remove alias fields not in model? keep only model columns
    # Transaction model columns: date, description, amount, type, transaction_type, category, subcategory, payment_method, merchant, account, notes, source, confidence_score, is_anomaly
    clean = {k:v for k,v in data.items() if k in ["date","description","merchant","amount","type","transaction_type","category","subcategory","payment_method","source","confidence_score","account","notes"]}
    tx = Transaction(id=str(uuid.uuid4()), user_id=user.id, **clean)
    # anomaly detection before commit? need historical amounts
    try:
        from app.ml.predictors.anomaly import detect_anomaly
        hist = db.query(Transaction.amount).filter(Transaction.user_id==user.id, Transaction.transaction_type=="expense").limit(200).all()
        hist_amounts = [float(x[0]) for x in hist]
        # detect for expense only; income not anomaly per spec
        is_anom = False
        if tx_type=="expense":
            res = detect_anomaly(float(clean["amount"]), hist_amounts, clean.get("category"))
            is_anom = res.get("is_anomaly", False)
            if is_anom:
                tx.is_anomaly = True
                # will create notification after commit
        else:
            tx.is_anomaly = False
    except Exception as e:
        print(f"anomaly check failed {e}")
        tx.is_anomaly = False
    db.add(tx)
    db.commit()
    db.refresh(tx)
    # post-commit anomaly notification
    if getattr(tx, 'is_anomaly', False):
        try:
            n = Notification(user_id=user.id, title="Unusual transaction detected", message=f"{tx.description} (₹{tx.amount}) marked as unusual spending.", type="alert")
            db.add(n)
            db.add(AgentInsight(user_id=user.id, title="Unusual Spending", content=f"Unusual transaction: {tx.description} in {tx.category} for ₹{tx.amount}", type="anomaly"))
            db.commit()
        except: pass
    # budget alerts for expense
    if tx_type=="expense":
        check_budget_alerts(user.id, tx.category, db)
    result = to_dict(tx)
    try:
        await manager.send_to_user(user.id, "transaction_created", result)
        await manager.send_to_user(user.id, "dashboard_refresh", {})
    except: pass
    return result

@router.put("/transactions/{tid}")
async def update_transaction(tid: str, payload: TransactionUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.id==tid, Transaction.user_id==user.id).first()
    if not tx: raise HTTPException(404, "Not found")
    updates = payload.model_dump(exclude_unset=True)
    # handle transaction_type alias
    if "transaction_type" in updates or "type" in updates:
        raw = updates.get("transaction_type") or updates.get("type")
        if raw:
            norm = str(raw).lower().strip()
            if norm not in ("income","expense"):
                raise HTTPException(400, "transaction_type must be income or expense")
            updates["transaction_type"] = norm
            updates["type"] = norm
    # if category manually corrected, store high confidence and allow future retraining architecture
    if "category" in updates and updates["category"]:
        # log correction for retraining (store insight)
        try:
            old_cat = tx.category
            new_cat = updates["category"]
            if old_cat != new_cat:
                # create agent insight for retraining signal - not exposing tokens
                db.add(AgentInsight(user_id=user.id, title="Category Correction", content=f"User corrected category from {old_cat} to {new_cat} for '{tx.description}' merchant '{tx.merchant}'", type="correction"))
                updates["confidence_score"] = 1.0
        except: pass
    for k,v in updates.items():
        if v is not None and k in ["date","description","merchant","amount","type","transaction_type","category","subcategory","payment_method","source","confidence_score","account","notes"]:
            setattr(tx,k,v)
    # re-check anomaly if amount/category changed
    try:
        from app.ml.predictors.anomaly import detect_anomaly
        hist = db.query(Transaction.amount).filter(Transaction.user_id==user.id, Transaction.transaction_type=="expense", Transaction.id!=tx.id).limit(200).all()
        hist_amounts = [float(x[0]) for x in hist]
        if getattr(tx, 'transaction_type', tx.type) == "expense":
            res = detect_anomaly(float(tx.amount), hist_amounts, tx.category)
            tx.is_anomaly = res.get("is_anomaly", False)
        else:
            tx.is_anomaly = False
    except: pass
    tx.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(tx)
    # re-check budget alerts on update if expense
    if getattr(tx, 'transaction_type', tx.type) == "expense":
        check_budget_alerts(user.id, tx.category, db)
    try: await manager.send_to_user(user.id, "transaction_updated", to_dict(tx))
    except: pass
    return to_dict(tx)

@router.delete("/transactions/{tid}")
async def delete_transaction(tid: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.id==tid, Transaction.user_id==user.id).first()
    if not tx: raise HTTPException(404, "Not found")
    db.delete(tx); db.commit()
    try: await manager.send_to_user(user.id, "transaction_deleted", {"id": tid})
    except: pass
    return {"status":"deleted"}

# ---- CSV IMPORT ----
@router.post("/transactions/import")
async def import_transactions(file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # security: file type and size
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Only .csv files allowed")
    contents = await file.read()
    if len(contents) > 5*1024*1024:
        raise HTTPException(400, "File too large. Max 5MB")
    if len(contents)==0:
        raise HTTPException(400, "Empty file")
    
    # Check if the uploaded file is an ML dataset instead of a statement
    from app.services.csv_parser import is_ml_dataset, detect_csv_format, parse_bank_statement_csv, parse_generic_csv
    if is_ml_dataset(contents):
        raise HTTPException(400, "This appears to be an ML training dataset rather than a bank statement. Upload it from ML Models > Train Transaction Categorizer.")
        
    print(f"[CSV IMPORT] format detection start, file={file.filename}, size={len(contents)}")
    try:
        fmt = detect_csv_format(contents)
    except Exception as e:
        print(f"[CSV IMPORT] format detection failed: {e}")
        fmt = "generic"
    print(f"[CSV IMPORT] format = {fmt}")
    try:
        if fmt == "bank_statement":
            detected = parse_bank_statement_csv(contents)
        else:
            detected = parse_generic_csv(contents)
    except Exception as e:
        print(f"[CSV IMPORT] parsing failed: {e}")
        raise HTTPException(400, f"Failed to parse CSV: {str(e)[:200]}")
    print(f"[CSV IMPORT] transactions detected = {len(detected)}")
    # transactions detected is count of logical transactions found (metadata ignored)
    total_rows = len(detected)
    imported = 0
    failed = 0
    duplicates = 0
    errors = []
    seen = set()
    # Process each normalized transaction through pipeline: categorization -> duplicate -> anomaly -> DB
    for idx, raw in enumerate(detected):
        try:
            # Safe normalized fields from parser (never log sensitive personal info)
            parsed_date = raw.get("date")
            # ensure date is date object
            if isinstance(parsed_date, str):
                try:
                    from datetime import datetime as dtu
                    # try parse string if needed (should already be date)
                    parsed_date = dtu.fromisoformat(parsed_date).date()
                except:
                    # fallback via _parse_date_safe? but parser already did
                    pass
            desc = raw.get("description") or f"Imported {idx+1}"
            # clean description: remove NaN, duplicate spaces (already done)
            desc = str(desc).strip()
            if desc.lower() in ("nan","none",""):
                desc = f"Transaction {parsed_date}"
            merchant = raw.get("merchant")
            amount = raw.get("amount")
            ttype = raw.get("transaction_type") or ("income" if str(raw.get("credit","")).strip() not in ("","-") else "expense")
            # Ensure amount positive and type correct (never use Balance)
            if amount is None or float(amount) <= 0:
                raise ValueError("invalid amount")
            amount = abs(float(amount))
            ttype = str(ttype).lower().strip()
            if ttype not in ("income","expense"):
                ttype = "expense" if amount>0 and raw.get("debit") else "income"
            # payment method: detect UPI if description contains UPI/
            pay = raw.get("payment_method")
            if not pay and "UPI/" in desc.upper():
                pay = "UPI"
            elif not pay:
                pay = "Bank Transfer"
            # Auto category via existing hybrid pipeline
            cat = raw.get("category")
            conf = 0
            if not cat or cat.strip() == "":
                try:
                    from app.ml.predictors.categorizer import categorize_transaction
                    cr = categorize_transaction(desc, merchant, amount, pay)
                    cat = cr.get("category", "Other")
                    conf = cr.get("confidence", 0)
                    if not merchant and cr.get("merchant"):
                        merchant = cr.get("merchant")
                    print(f"[CSV IMPORT] normalized category {cat} for desc {desc[:30]}")
                except Exception as e:
                    print(f"[CSV IMPORT] categorize failed {e}")
                    cat="Other"; conf=0
            else:
                conf = 1.0
            # duplicate check per spec: user_id + date + amount + description
            dup_key = (str(parsed_date), round(float(amount),2), desc.lower().strip())
            if dup_key in seen:
                duplicates += 1
                print(f"[CSV IMPORT] duplicate in file at idx {idx}")
                continue
            seen.add(dup_key)
            exists = db.query(Transaction).filter(
                Transaction.user_id==user.id,
                Transaction.date==parsed_date,
                Transaction.amount==round(float(amount),2),
                Transaction.description==desc
            ).first()
            if exists:
                duplicates += 1
                print(f"[CSV IMPORT] duplicate in DB at idx {idx}")
                continue
            # anomaly check (real user history)
            is_anom = False
            try:
                from app.ml.predictors.anomaly import detect_anomaly
                hist = db.query(Transaction.amount).filter(Transaction.user_id==user.id, Transaction.transaction_type=="expense").limit(100).all()
                hist_amounts = [float(x[0]) for x in hist]
                if ttype=="expense":
                    r = detect_anomaly(float(amount), hist_amounts, cat)
                    is_anom = r.get("is_anomaly", False)
            except Exception as e:
                print(f"[CSV IMPORT] anomaly check skip {e}")
                pass
            tx = Transaction(
                id=str(uuid.uuid4()),
                user_id=user.id,
                date=parsed_date,
                description=desc,
                merchant=merchant,
                amount=round(float(amount),2),
                type=ttype,
                transaction_type=ttype,
                category=cat,
                subcategory=None,
                payment_method=pay,
                source="csv",
                confidence_score=conf,
                is_anomaly=is_anom
            )
            db.add(tx)
            imported += 1
        except Exception as e:
            failed += 1
            msg = str(e)
            # Never log sensitive personal info
            if len(errors) < 5:
                errors.append(f"Row {idx+1}: {msg[:80]}")
            print(f"[CSV IMPORT] failed idx {idx}: {msg[:120]}")
            continue
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[CSV IMPORT] commit failed {e}")
        raise HTTPException(500, f"Import commit failed: {e}")
    print(f"[IMPORT] detected = {total_rows}")
    print(f"[IMPORT] normalized = {len(detected)}")
    print(f"[IMPORT] duplicate = {duplicates}")
    print(f"[IMPORT] inserted = {imported}")
    print(f"[IMPORT] failed = {failed}")
    # after import, check budget alerts for imported categories
    try:
        cats = db.query(Transaction.category).filter(Transaction.user_id==user.id, Transaction.source=="csv").distinct().all()
        for (c,) in cats:
            if c: check_budget_alerts(user.id, c, db)
    except Exception as e:
        print(f"[CSV IMPORT] budget alert check failed {e}")
    try:
        await manager.send_to_user(user.id, "transactions_imported", {"imported": imported})
        await manager.send_to_user(user.id, "dashboard_refresh", {})
    except: pass
    return {
        "total": total_rows,
        "total_rows": total_rows,
        "transactions_detected": len(detected),
        "imported": imported,
        "duplicates": duplicates,
        "failed": failed,
        "errors": errors,
        "format": fmt
    }

@router.post("/transactions/recategorize")
async def recategorize_transactions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Recategorize authenticated user's existing transactions using the enhanced
    Indian bank / UPI description preprocessor and hybrid categorization pipeline.
    """
    from app.ml.predictors.categorizer import categorize_transaction
    from app.ml.preprocessing.text_features import extract_merchant

    txs = db.query(Transaction).filter(Transaction.user_id == user.id).all()
    changed = 0
    unchanged = 0

    for tx in txs:
        current_merchant = tx.merchant
        if not current_merchant:
            extracted = extract_merchant(tx.description)
            if extracted and extracted != tx.description:
                current_merchant = extracted
                tx.merchant = current_merchant

        amt = float(tx.amount) if tx.amount else None
        res = categorize_transaction(tx.description, current_merchant, amt, tx.payment_method)
        new_cat = res.get("category", "Other")
        conf = res.get("confidence", 0.0)

        if res.get("merchant") and not tx.merchant:
            tx.merchant = res.get("merchant")

        # Update if a reliable non-Other category is found or category updated
        if new_cat and new_cat != "Other" and (tx.category == "Other" or tx.category != new_cat):
            tx.category = new_cat
            tx.confidence_score = conf
            changed += 1
        elif tx.category == "Other" and new_cat == "Other":
            unchanged += 1
        else:
            unchanged += 1

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to commit recategorization: {e}")

    # Refresh dashboard and budget alerts for any updated categories
    try:
        cats = db.query(Transaction.category).filter(Transaction.user_id==user.id).distinct().all()
        for (c,) in cats:
            if c: check_budget_alerts(user.id, c, db)
    except Exception as e:
        print(f"[RECATEGORIZE] budget alert check failed: {e}")

    try:
        await manager.send_to_user(user.id, "transactions_imported", {"imported": changed})
        await manager.send_to_user(user.id, "dashboard_refresh", {})
    except:
        pass

    return {
        "processed": len(txs),
        "changed": changed,
        "unchanged": unchanged
    }
