import React from 'react'
export const Button = ({children, ...props}: any)=> <button {...props} className={`btn-primary disabled:opacity-50 ${props.className||''}`}>{children}</button>
