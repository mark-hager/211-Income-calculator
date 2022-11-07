"""
Python implementation of Hannah Newton's Excel-based income calculator for
use by King County 2-1-1 specialists. @author:mhager
Flask app takes inputs from the html form to determine eligibility for various
benefits programs based upon the annual income, size of the household, and
whether the household includes any minor children.
Also estimates birthyear and client age based upon the client's age or birthdate,
respectively.
"""

# used for formatting user inputs by stripping dollar signs and commas
import re
# math package used for rounding
import math
# import Flask
from flask import Flask, flash, render_template, request
# wtforms for input validation
from wtforms import Form, BooleanField, StringField, validators


from markupsafe import escape

# create Flask object
app = Flask(__name__)

app.config['SECRET_KEY'] = 'vbdfffs76VF'

# only one route since the calculator is only one page
@app.route("/", methods = ['POST', 'GET'])
def main():
    # get the data from the form submission
    if request.method == 'POST':

        # fields that are required in order to calculate the AMI, FPL & SMI
        household_size = int(request.form['household_size'])
        income_type = request.form['income_type']
        raw_income = int(request.form['income_amount'])

        # optional fields used to determine potential program eligibility

        # must use form.get to get value of checkbox in Flask
        has_children = request.form.get('has_children')
        monthly_rent = int(request.form['monthly_rent'])

        if income_type == "Monthly":
            annual_income = raw_income * 12
        else:
            # check that income isn't negative or something else invalid first
            annual_income = raw_income

        household = NewHousehold(annual_income, household_size, has_children, monthly_rent)

        income = annual_income
        FPL = household.fpl
        SMI = household.smi
        AMI = household.ami

        return render_template('app.html', household_size = household_size, annual_income = income, fpl = FPL, smi = SMI, ami = AMI)
        
    return render_template('app.html')

class NewHousehold:
    """
    Represents a household for the purposes of determining eligibility for various
    benefit programs. Includes fields for annual income and household size as well as
    a boolean reflecting whether or not the household includes minor children.
    Also has fields for client age and client dob for the purposes of estimating birth year
    and calculating the client's age, respectively.
    """
    def __init__(self, annual_income, household_size, has_children, rent_amount, client_age = None, client_dob = None):
        # client_dob and client_age are used for calculating age from birthdate
        # and estimating year of birth from age, respectively 
        self.client_age = client_age
        self.client_dob = client_dob
        # the FPL, SMI and AMI are calculated based on the annual income and household size
        self.annual_income = annual_income
        self.household_size = household_size
        # initialized as None until we calculate the FPL, SMI and AMI via their
        # respective methods
        self.fpl = None
        self.smi = None
        self.ami = None
        # has_children defaults to False; is true only if checkbox in form is selected
        self.has_children = has_children
        # used for determininig eligibility to HSP which requires a rent to income ratio of 1:1.5
        self.rent_amount = rent_amount

        self.calculate_fpl()
        self.calculate_smi()
        self.calculate_ami()

    def calculate_fpl(self):
        """
        Calculates the Federal Poverty Level based on HHS 2022 guidelines
        https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines
        """

        # FPL is calculated with a base rate times an additional rate per person
        fpl_base = 8870
        fpl_rate_per_person = 4720
        # calculate the FPL by dividing income by the base rate + household size
        # * the rate per person
        fpl = math.ceil(self.annual_income / ((self.household_size * fpl_rate_per_person)
                                        + fpl_base) * 100)
        # format as percentage
        fpl = "{}%".format(fpl)
        self.fpl = fpl  # assign the calculated Federal Poverty Level percentage to our object


    def calculate_smi(self):
        """
        Calculates the State Median Income based on DSHS 2022 guidelines
        https://www.dshs.wa.gov/esa/eligibility-z-manual-ea-z/state-median-income-chart
        """

        # SMI is calculated with separate base rates depending on household size
        # for families of 5 or less, and families of 6 or more
        smi_base_household_5_or_less = 38940
        smi_base_household_6_or_more = 142776
        # the rate for each person in a household of 5 or less
        smi_rate_household_5_or_less = 17304
        # the rate for each person in a household of 6 or more
        smi_rate_household_6_or_more = 3240

        # calculate the SMI depending on household size
        if self.household_size < 7:
            smi = self.annual_income / ((self.household_size * smi_rate_household_5_or_less)
                                + smi_base_household_5_or_less) * 100
        elif self.household_size > 6:
            smi = self.annual_income / (smi_base_household_6_or_more +
                                ((self.household_size - 6) * (smi_rate_household_6_or_more))) * 100
        # round the SMI up
        smi = math.ceil(smi)
        # format as percentage
        smi = "{}%".format(smi)
        self.smi = smi  # assign the calculated State Median Income percentage to our object


    def excel_ceil(self, num):  # emulating excel's ceiling function to directly copy Hannah's formula
        return 50 * math.ceil(float(num) / 50)

    def calculate_ami(self):
        """
        Calculates the Area Median Income based on HUD 2022 guidelines
        https://www.huduser.gov/portal/datasets/il/il2022/2022summary.odn
        Currently rounding final AMI percentage as Hannah appears to be doing; need to confirm that this is correct.
        Previously I was using floor to always round down which created discrepancy

        """
        # AMI is calculated from the median annual income for a family of 4
        ami_base_household_of_4 = 129400
        # 80% low-income limit for a family of 4; for more detail read https://www.huduser.gov/portal/datasets/il/il2022/2022ILCalc3080.odn
        ami_base_80_percent = 95300
        # theoretical median income for a household of 0
        ami_base_0 = 77640
        # 80% of the median income for a household of 0
        ami_base_0_80_percent = 57180
        # for calculations when the initial AMI is between 70% and 80%
        ami_base_between_70_and_80 = 113125
        # initialize to false
        check_80_percent = False

        # calculate initial percentage to determine if it falls above or below 70%
        if self.household_size < 5:
            initial_ami = self.annual_income / ((ami_base_0) + (self.household_size * (ami_base_household_of_4 * .10))) * 100
            ami_80_cap = ami_base_0_80_percent + ami_base_80_percent * (self.household_size * .10)       #80% CAP calculation in Hannah's excel calculator
        elif self.household_size > 4:
            initial_ami = self.annual_income / ((ami_base_household_of_4 * .08) * (self.household_size - 4) + ami_base_household_of_4) * 100
            ami_80_cap = ami_base_80_percent + (ami_base_80_percent * (self.household_size - 4) * .08)

        ami_80_cap = self.excel_ceil(ami_80_cap)
        # calculate Hannah's Base 100% (C8), a massaged 100% AMI number
        if self.household_size < 5:
            ami_massaged_100_percent = ami_base_0 + (ami_base_household_of_4 * 0.1 * self.household_size)
        elif self.household_size > 4:
            ami_massaged_100_percent = ami_base_household_of_4 + (ami_base_household_of_4 * 0.08 * (self.household_size - 4))


        # AMI adjustment for incomes that would normally fall between 70% and 80% of the AMI
        if initial_ami >= 71 and initial_ami <= 81:
            if self.household_size < 5:
                adjusted_ami = self.annual_income / (ami_base_between_70_and_80 + ((self.household_size - 4) * ami_base_between_70_and_80 * .10)) * 100
            else:
                adjusted_ami = self.annual_income / (ami_base_between_70_and_80 + ((self.household_size - 4) * ami_base_between_70_and_80 * .08)) * 100

        else:
            adjusted_ami = initial_ami

        # AMI adjustments for incomes that would fall under the 50% CAP
        cap_50 = ami_massaged_100_percent / 2
        cap_50 = 50 * round(cap_50 / 50)
        check_50_percent = False

        if self.annual_income > cap_50 and adjusted_ami < 51:
            check_50_percent = True

        # 80% CHECK:
        if self.annual_income > ami_80_cap and adjusted_ami < 81:
            check_80_percent = True

        ami = round(adjusted_ami)
        if check_50_percent == True:
            ami = 51
        if check_80_percent == True:
            ami = 81
        # format as percentage
        ami = "{}%".format(round(ami))
        self.ami = ami  # assign the calculated Area Median Income percentage to our object

class ProgramEligibility: 
    """
    Determines eligiblity for various benefits programs from an instance
    of NewHousehold to check program requirements against the FPL, SMI, AMI
    and household composition of the household.
    """
    eligibile_for_hsp = False
    def __init__(self, household):
        self.household = household
    
    def hsp_eligibility(self):
        """
        Determines eligibility for Housing Stability Project:
        Area Median Income must be less than or equal to 50% and
        rent to income ratio must be less than or equal to 1:1.5
        """
        if self.household.rent_amount is None:
            print("Please enter a rental amount to determine HSP eligibility")
            return
        if self.household.household.ami > 0.5:
            print("Income too high: AMI was above 0.5")
            self.eligibile_for_hsp = False
        if ((self.household.income / 12) / self.household.rent) < 1.5:
            print("Income to rent ratio was too low; must be at least 1.5:1")
            self.eligibile_for_hsp = False
        return


household_test = NewHousehold(30000, 1, None, None, None, None)     
test_fpl = household_test.fpl
test_smi = household_test.smi
test_ami = household_test.ami
test_string = (f"The FPL is {test_fpl}, the SMI is {test_smi}, the AMI is {test_ami}")
eligibility_test = ProgramEligibility(household_test)
eligibility_test.hsp_eligibility()

print(household_test.ami)
