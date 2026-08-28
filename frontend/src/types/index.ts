export interface Transaction { id:string; date:string; description:string; amount:number; type:string; category:string; payment_method?:string; merchant?:string; account?:string; notes?:string}
export interface Budget { id:string; category:string; amount:number; period:string; spent?:number; remaining?:number; pct?:number}
export interface Goal { id:string; name:string; target_amount:number; current_amount:number; target_date?:string}
export interface Asset { id:string; name:string; symbol?:string; type:string; quantity:number; purchase_price:number; current_price?:number; invested?:number; current_value?:number; pnl?:number; pct?:number}
