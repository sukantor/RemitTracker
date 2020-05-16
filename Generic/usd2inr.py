from bs4 import BeautifulSoup
import os
import sys
import time
import requests
import cloud4rpi
import pandas as pd


# cloud4rpi
"""
Get free token from https://cloud4rpi.io/
Set Token  as Enviaronment Variable
pi@pizerow:~ $ cat /etc/environment
CLOUD4RPI_DEVICE_TOKEN=<token>
-- or --
pi@pizerow:~ $ export CLOUD4RPI_DEVICE_TOKEN=<token>
"""
CLOUD4RPI_DEVICE_TOKEN = os.environ.get("CLOUD4RPI_DEVICE_TOKEN")

source_currency = "USD"
destination_currency = "INR"
source_amount = 1000


def TransferWise():
    success = False
    data = 0
    base_url_transferwise = "https://transferwise.com"
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
            print("Error Accessing ", uri, "Error Code: ", req_ob.status_code)
    except Exception as e:
        print(e)
    return(success, data)


def InstaRemRate():
    base_url_instarem = "https://www.instarem.com"
    instarem_bank_account_id = 58
    params = {
        "source_currency": source_currency,
        "destination_currency": destination_currency,
        "instarem_bank_account_id": instarem_bank_account_id,
        "source_amount": source_amount
    }
    success = False
    data = dict()
    try:
        req_ob = requests.get(base_url_instarem + "/api/v1/public/transaction/computed-value", params=params)
        result = req_ob.json()
        data = result["data"]
        success = result["success"]
    except Exception as e:
        print(e)
    return(success, data)


def RemitlyRate():
    base_url_remitly = "https://www.remitly.com"
    success = False
    data = 0
    try:
        df_list = pd.read_html(requests.get(base_url_remitly + "/us/en/india/pricing").content)
        economy = df_list[-1][1][0]
        if "Remitly Economy" in economy:
            success = True
            data = float(df_list[-1][1][1].replace("Everyday rate", "").replace("₹", ""))
    except Exception as e:
        print(e)
    return(success, data)


def XoomRate():
    base_url_xoom = "https://www.xoom.com"
    success = False
    data = 0
    try:
        req_ob = requests.get(base_url_xoom + "/india/send-money")
        soup = BeautifulSoup(req_ob.text, "lxml")
        rate_data = soup.find("div", {"class": "js-exchange-rate"})
        data = round(float(rate_data.p.contents[0].split()[3]), 2)
        success = True
    except Exception as e:
        print(e)
    return(success, data)


def RiaRate():
    base_url_ria = "https://www.riamoneytransfer.com"
    success = False
    data = 0
    try:
        response_session = requests.get(base_url_ria + "/api/Authorization/session")
        if response_session.status_code == 200:
            bearer = response_session.headers.get("bearer")
            header_auth = {"Authorization": f"Bearer {bearer}"}
            response_auth = requests.get(base_url_ria + "/api/Calculator/Initialize", headers=header_auth)
            if response_auth.status_code == 200:
                token = response_auth.headers.get("bearer")
                header_calc = {"Authorization": f"Bearer {token}", "Content-Type": "application/json;charset=UTF-8"}
                # Replace "countryTo": "IN" with Other Cuntry Code if needed
                payload = {"Selections": {"amountFrom": "", "countryTo": "IN", "currencyTo": None}}
                response_rate = requests.post(base_url_ria + "/api/MoneyTransferCalculator/Calculate", headers=header_calc, json=payload)
                if response_rate.status_code == 200:
                    data = round(response_rate.json()["model"]["transferDetails"]["calculations"]["exchangeRate"], 2)
                    success = True
    except Exception as e:
        print(e)
    return(success, data)


def main():
    try:
        device = cloud4rpi.connect(CLOUD4RPI_DEVICE_TOKEN)
        status, remitdata = InstaRemRate()
        if status:
            rate_instarem = round(remitdata["destination_amount"]/1000, 2)
            fx_rate = round(remitdata["fx_rate"], 2)
        else:
            rate_instarem = 0
        # Remitly
        status, rate_remitly = RemitlyRate()
        # Xoom
        status, rate_xoom = XoomRate()
        # Ria Rate
        status, rate_ria = RiaRate()
        # Transferwise Rate
        status, rate_transferwise = TransferWise()
        datetime = time.strftime("%m/%d/%y %H:%M:%S")
        print(f"FX Rate: {fx_rate} Instarem: {rate_instarem} Remitly: {rate_remitly} Xoom: {rate_xoom} Ria: {rate_ria}, TransferWise: {rate_transferwise}  Last Updated {datetime}")
        rate_all = {
            "instarem": rate_instarem,
            "remitly": rate_remitly,
            "xoom": rate_xoom,
            "ria": rate_ria,
            "transferwise": rate_transferwise
            }
        try:
            variables = {
                "Fx Rate": {
                    "type": "numeric" if fx_rate else "string",
                    "value": fx_rate if fx_rate else "N/A"
                },
                "Instarem": {
                    "type": "numeric" if rate_instarem else "string",
                    "value": rate_instarem if rate_instarem else "N/A"
                },
                "Remitly": {
                    "type": "numeric" if rate_remitly else "string",
                    "value": rate_remitly if rate_remitly else "N/A"
                },
                "Xoom": {
                    "type": "numeric" if rate_xoom else "string",
                    "value": rate_xoom if rate_xoom else "N/A"
                },
                "Ria": {
                    "type": "numeric" if rate_ria else "string",
                    "value": rate_ria if rate_ria else "N/A"
                },
                "TransferWise": {
                    "type": "numeric" if rate_transferwise else "string",
                    "value": rate_transferwise if rate_transferwise else "N/A"
                }
            }
            device.declare(variables)
            # Uncomment Below 2 Lines in first run after Cloud4Rpi Device Creation
            # device.publish_config()
            # time.sleep(1)
            print("Uploading  Data to cloud4rpi")
            device.publish_data()
            lastrun = time.time()
        except Exception as e:
            error = cloud4rpi.get_error_message(e)
            cloud4rpi.log.exception("ERROR! %s %s", error, sys.exc_info()[0])
    except KeyboardInterrupt:
        epd2in13_V2.epdconfig.module_exit()
        exit()


if __name__ == "__main__":
    main()
