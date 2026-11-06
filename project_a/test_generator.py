import random
try:
    from project_a.models import SalaryProfile
except ImportError:
    from models import SalaryProfile

def generate_test_cases():
    test_cases = []
    
    # 1. Exact Threshold Cases (Rebate cliffs and slab transitions)
    critical_gross_points = [
        0, 250000, 300000, 500000, 500010, 700000, 700010, 750000, 775000,
        1000000, 1200000, 1275000, 1500000, 5000000, 5000010, 10000000, 20000000
    ]
    
    for gross in critical_gross_points:
        test_cases.append(SalaryProfile(
            gross_salary=gross,
            basic_salary=gross * 0.4,
            da=gross * 0.1,
            hra_received=gross * 0.2,
            rent_paid=gross * 0.15,
            is_metro=True,
            sec_80c=min(150000.0, gross * 0.1),
            sec_80ccd_1b=25000.0 if gross > 500000 else 0.0,
            sec_80d_self=25000.0 if gross > 500000 else 0.0,
            sec_80d_parents=50000.0 if gross > 1000000 else 0.0,
            parents_senior=True,
            home_loan_interest_self_occupied=200000.0 if gross > 1500000 else 0.0
        ))
        
    # 2. Random Monte Carlo distribution to complete 200 cases
    random.seed(42)
    while len(test_cases) < 200:
        gross = random.randint(300000, 30000000)
        test_cases.append(SalaryProfile(
            gross_salary=float(gross),
            basic_salary=float(gross * 0.4),
            da=float(gross * 0.05),
            hra_received=float(gross * 0.15),
            rent_paid=float(gross * 0.12),
            is_metro=random.choice([True, False]),
            sec_80c=float(random.randint(0, 200000)),
            sec_80ccd_1b=float(random.choice([0, 25000, 50000])),
            sec_80d_self=float(random.randint(0, 30000)),
            sec_80d_parents=float(random.randint(0, 60000)),
            parents_senior=random.choice([True, False]),
            home_loan_interest_self_occupied=float(random.choice([0, 100000, 200000, 300000]))
        ))
    return test_cases

PLAIN_LANGUAGE_QUERIES = [
    # Category 1: Clean & Complete (Direct Calculations)
    "My annual gross is 14.5 Lakhs, basic is 6 Lakhs, I pay 25k monthly rent in Bengaluru. 80C is maxed out at 1.5L.",
    "Gross salary 8 LPA, no investments, rent is zero staying with parents.",
    "Gross 35 Lakhs, paying 45k/month rent in Mumbai, basic 15L, home loan interest 2.4L self occupied. Max 80C done.",
    "Annual CTC 12,00,000, basic 5,00,000, 80C invested 1,50,000, medical self 25000, non-metro rent 15000 monthly.",
    "Total salary 50 Lakhs, basic 25 Lakhs, no rent, 80C 1.5L, 80CCD(1B) 50k, parents non-senior health insurance 25k.",
    "Gross salary is 7.2 Lakhs per annum with no deductions or investments. Living in own house.",
    "Annual income from salary is 9.5 LPA, basic 4 LPA, HRA 1.5 LPA, actual rent 12k/month in Jaipur, 80C 1L.",
    "Fixed gross salary 16,00,000, basic salary 8,00,000, rent 30,000 per month in Delhi metro, 80C full 1.5L.",
    "Annual gross 28 LPA, basic 12 LPA, home loan interest self-occupied 2,00,000, 80C 1.5L, NPS 50k.",
    "CTC is 10,50,000 INR. Basic is 4,20,000. Rent paid is 18,000/month in Hyderabad. 80C is 1,20,000.",
    "Gross 4.5 LPA, zero deductions, no rent paid.",
    "My salary is 15 LPA flat, no HRA component, basic is 7.5L, invested 1.5L in PPF and 50k in NPS 80CCD(1B).",
    
    # Category 2: Hinglish & Casual Phrasing
    "Bhai meri CTC 22 LPA hai, 50k NPS me dale hai aur 1.5 lakh PPF me. Mummy papa senior citizen hai unka health insurance 45000 bhara.",
    "Salary 6.5 lakh hai. Kuch tax bachega kya? Rent wagera kuch nahi hai.",
    "Mera package 18 LPA hai, Pune me rehta hu aur rent 20k per month deta hu. Basic 7.2L hai. 80C me 1.5L invest kiya hai.",
    "CTC 30 lakh hai annual. Basic 12 lakh, rent 35000 per month in Mumbai. Mediclaim khudka 20000 aur parents (senior) ka 50000.",
    "Gross salary 9 lakh hai, 80C me 1 lakh LIC me gaya, baki koi deduction nahi hai. Rent zero hai.",
    "Mera saal ka 14 lakh banta hai salary se. Basic 6 lakh hai, HRA 2 lakh milta hai, actual rent 18k deta hu Gurgaon me. 80C full.",
    "Annual 25 LPA package, home loan interest 1.8 lakh bhar raha hu. 80C poora 1.5L bhara hai.",
    "Bhai 7.5 LPA income hai, PF ka 60k cut hota hai. Aur koi investment nahi hai.",
    "CTC 40 LPA, Delhi metro me flat rent 40k monthly, basic 18L, 80C 1.5L aur 50k NPS tier 1 contribution.",
    "Salary 11.2 LPA, medical insurance for self 25000, no rent because staying in hometown.",
    "Mera gross package 13.5 LPA hai. Basic salary 40% hai, rent 22000 per month Bangalore me hai. 80C maxed out.",
    "Total salary 19 LPA, parents senior citizen hain unka 40000 mediclaim bhara, mera 20000. 80C 1.5L kiya.",

    # Category 3: Incomplete & Ambiguous Inputs (Must trigger clarifying questions)
    "I make 12 LPA and pay rent in Pune.", # Missing rent amount
    "Gross CTC 18 Lakhs, medical insurance for parents is 40000.", # Missing parents senior citizen age status
    "I want to calculate my tax for this year. Can you tell me which regime is better?", # Missing salary entirely
    "Paying 30k rent every month, invested in ELSS. How much tax?", # Missing CTC/Gross salary
    "Salary 15 LPA. Rent 20k per month.", # Missing city type (metro vs non-metro)
    "My salary is 20 LPA, basic is 8 LPA, and I have high rent in Mumbai.", # Missing exact rent amount
    "Gross salary 10 Lakhs, want to claim 80D medical deduction.", # Missing medical insurance amount
    "Annual CTC 24 Lakhs, paying home loan EMI 60,000 every month.", # Missing interest vs principal split
    "I have 80C investment of 1.5 Lakhs and pay 25k monthly rent.", # Missing gross income
    "Salary is 16 LPA, how much tax can I save under 80D?", # Missing policy expenditure amounts
    "Package 14 LPA, living in rented house in Kolkata.", # Missing monthly rent amount
    "My CTC is 9 LPA and I invest in mutual funds.", # Missing ELSS/80C specific amount
    "CTC 32 LPA, paying 50k rent in Bangalore, basic unknown.", # Missing basic/DA ratio confirmation
    "Gross 13 LPA, invested money in NPS.", # Missing NPS contribution amount

    # Category 4: Contradictory & Malformed Cases (Must flag or seek resolution)
    "Gross salary 10 LPA, and my basic salary is 15 LPA.", # Basic cannot exceed gross
    "My annual salary is 12 Lakhs and I pay 1.5 Lakhs rent every month.", # Rent exceeds total salary
    "Gross CTC 8 LPA, claiming 80C of 3 Lakhs under old regime.", # Over limit / clarify cap
    "I earn 15 LPA, pay 0 rent, but want to claim 2 Lakhs HRA exemption.", # HRA claimed without rent
    "Gross salary is minus 5 Lakhs.", # Invalid negative salary
    "CTC 25 LPA, self home loan interest paid is 4 Lakhs.", # Exceeds 24(b) statutory ceiling
    "Gross salary is zero, but have 1.5L 80C and 50k NPS to deduct.", # Zero taxable base
    "My salary is 18 LPA, I live in my own house, but paying 30k rent to my brother without receipts.",
    "CTC is 50,000 per month, annual gross is 20 Lakhs.", # Monthly doesn't match annual
    "Earning 12 LPA, parents age 45, claiming senior citizen health insurance 50k.", # Parents not seniors (<60)
    "Gross salary 6 LPA, 80C 1.5L, 80D 50k, 80CCD 50k, HRA 2L, total deductions 5L.", # Borderline zero tax profile
    "CTC 7.5 LPA, basic 3 LPA, rent 10k/month in Delhi, but no HRA in payslip." # Rent paid without HRA component
]