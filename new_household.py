"""
Class containing methods for representing a household
in order to estimate eligibility for 
various state assistance programs based on
income measures and household size and composition.
"""
from datetime import datetime, date

import income_measures
# uses program eligibility requirements cefined in program_requirements.py
from program_eligibility import *

class NewHousehold:
    """
    Uses validated data from the flask wtform to create
    a representation of a household for the purposes
    of determining income measures and program eligibility.
    """
    # default args for has_children, rent_amount and client_dob since these are optional fields
    def __init__(self, form, raw_dob):

        # required fields for calculating income measures
        self.annual_income = self.get_annual_income(form.income_amount.data,
                                                    form.income_type.data)

        self.household_size = form.household_size.data

        # Calculate income measures using methods from income_measures.py
        self.ami = income_measures.calculate_ami(self)
        self.fpl = income_measures.calculate_fpl(self)
        self.smi = income_measures.calculate_smi(self)

        # optional fields
        if hasattr(form, 'has_children'):
            self.has_children = form.has_children.data
        # monthly_rent is a string formatted as currency
        if hasattr(form, 'monthly_rent') and form.monthly_rent.data:
            # convert the monthly rent string to float and strip out the commas
            self.monthly_rent = float(form.monthly_rent.data.replace(",", ""))
        if raw_dob is not None:
            self.age = self.calculate_age(raw_dob)

        self.program_eligibility()


    def get_annual_income(self, income_string, income_type):
        """
        Gets the income amount and type from the wtform and uniformly saves it as the annual
        income for the NewHousehold object by multiplying income amount by 12 when the income 
        type is monthly.
        """
        income_amount = float(income_string.replace(",", ""))
        # convert flask_wtf decimal field to float for calculations
        if income_type == "Monthly":
            annual_income = float(income_amount * 12)
        else:
            annual_income = float(income_amount)
        return annual_income

    def calculate_age(self, raw_dob):
        """
        Calculates the client's age from their DOB.
        *TODO* validate dob by using custom wtform validator
        to give an error if DOB is invalid e.g a future date.
        """
        # try calculating age from the raw DOB string
        try:
            dob = datetime.strptime(
                        raw_dob,
                        '%Y-%m-%d')
            # roughly account for leapyears in calendar year
            age = int((datetime.today() - dob).days / 365.2425)

        except ValueError:
            return

        # check that the age is somewhat realistic
        if 0 < age > 120:
            return age

    def program_eligibility(self):
        """
        Determines eligiblity for various benefits programs using the FPL, SMI, AMI
        and household composition, using the eligibility requirements
        defined in each of the program functions in program_eligibility.py
        """

        # programs that can be screened w/out rent
        apple_health = apple_health_eligibility(self)
        wa_basic_food = basic_food_eligibility(self)
        liheap = liheap_eligibility(self)
        pse_help = pse_help_eligibility(self)
        elia = elia_eligibility(self)

        # check for eligibility only if rent amount entered
        if hasattr(self, 'monthly_rent') and self.monthly_rent > 0:
            hsp = hsp_eligibility(self)
        else:
            hsp = False

        # initialize list to hold program names that the client/household may
        # be eligible for; dynamically displayed by jinja template
        self.programs = []
        if wa_basic_food:
            self.programs.append("Washington Basic Food Program")
        if apple_health:
            self.programs.append("Apple Health")
        if hsp:
            self.programs.append("Housing Stability Project")
        if liheap:
            self.programs.append("Low Income Home Energy Assistance Program (LIHEAP)")
        if pse_help:
            self.programs.append("PSE HELP - PSE Customers Only")
        if elia:
            self.programs.append("Emergency Low Income Assistance (ELIA) - SCL Customers Only")
