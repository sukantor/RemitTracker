import requests

def TransferWise():
    success = False
    data = 0
    base_url_transferwise = "https://transferwise.com"
    source_currency = "USD"
    destination_currency = "INR"
    source_amount = 1000
    params = {
        "sourceCurrency": source_currency, 
        "targetCurrency": destination_currency,
        "sourceAmount": source_amount
    }
    uri = base_url_transferwise + "/gateway/v2/quotes/"
    try:
        req_ob = requests.post(uri, json=params)
        if req_ob.status_code == 200:
            result = req_ob.json()
            for eachtype in result["paymentOptions"]:
                if "DIRECT_DEBIT" in eachtype["payIn"]:
                    data = round(eachtype["targetAmount"]/source_amount, 2)
                    success = True
                    break   
        else:
            print("Error Accessing " , uri , "Error Code: ", req_ob.status_code)
    except Exception as e:
        print(e)
    return(success, data)
    
def main():
    print(TransferWise())

if __name__ == "__main__":
    main()