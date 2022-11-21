# 211-Income-calculator
Calculates program eligibility based on income and household size
Python implementation of Hannah Newton's Excel-based income calculator for 
use by King County 2-1-1 specialists.

# Potential issues
SMI is always rounded up, whereas Hannah's excel calculator truncates the initial value
when monthly income is entered and the household size is less than 7:
    IF(AND(C7>0,C8<7),ROUNDDOWN((C7*12)/(J2+(C8*J3)),4),
This excel rounds the initial value down to the lowest 4 decimal places.
If annual income is entered or the household size is greater than 7 then
this rounddown function is not applied and the initial value is always
rounded up to the nearest integer.