### core/utils.py
import re

def generate_upi_link(upi_id, name, amount, note):
    return f"upi://pay?pa={upi_id}&pn={name}&am={amount}&tn={note}&cu=INR"

def parse_sms_data(sms):
    amount_match = re.search(r'₹(\d+\.?\d*)', sms)
    merchant_match = re.search(r'to (.*?) via', sms)

    if amount_match and merchant_match:
        amount = amount_match.group(1)
        merchant = merchant_match.group(1).strip()
        lower_merchant = merchant.lower()

        category_map = {
            'zomato': 'Food',
            'swiggy': 'Food',
            'uber': 'Transport',
            'ola': 'Transport',
            'amazon': 'Shopping',
            'flipkart': 'Shopping',
            'pharmeasy': 'Health',
            'medlife': 'Health',
        }

        category = 'Other'
        for key in category_map:
            if key in lower_merchant:
                category = category_map[key]
                break

        return {
            'amount': amount,
            'category': category,
            'description': f"GPay: {merchant}",
            'status': 'Paid'
        }
    return None
