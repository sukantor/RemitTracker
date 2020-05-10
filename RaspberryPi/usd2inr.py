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
rpidir = "/home/pi/cloud4rpi-raspberrypi-python"
sys.path.append(rpidir)
import rpi

# e-Paper Display https://github.com/waveshare/e-Paper
libdir = "/home/pi/e-Paper/RaspberryPi&JetsonNano/python/lib"
sys.path.append(libdir)
from waveshare_epd import epd2in13_V2
from PIL import Image, ImageDraw, ImageFont
# e-Paper Fonts
picdir = "/home/pi/e-Paper/RaspberryPi&JetsonNano/python/pic"
font20 = ImageFont.truetype(os.path.join(picdir, "Font.ttc"), 20)
font24 = ImageFont.truetype(os.path.join(picdir, "Font.ttc"), 24)


def get_icon(name):
    iconsdir = os.path.dirname(__file__)
    if 'instarem' in name:
        return Image.open(os.path.join(iconsdir, "../images/instarem.ico"))
    elif 'remitly' in name:
        return Image.open(os.path.join(iconsdir, "../images/remitly.png"))
    elif 'xoom' in name:
        return Image.open(os.path.join(iconsdir, "../images/xoom.png"))
    elif "ria" in name:
        return Image.open(os.path.join(iconsdir, "../images/ria.png"))
    else:
        return None


def InstaRemRate():
    base_url_instarem = "https://www.instarem.com"
    source_currency = "USD"
    destination_currency = "INR"
    instarem_bank_account_id = 58
    source_amount = 1000
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
        lastrun = time.time() - 300
        device = cloud4rpi.connect(CLOUD4RPI_DEVICE_TOKEN)
        epd = epd2in13_V2.EPD()
        epd.init(epd.FULL_UPDATE)
        # epd.Clear(0xFF)
        image = Image.new("1", (epd.height, epd.width), 255)  # 255: clear the frame
        draw = ImageDraw.Draw(image)
        epd.displayPartBaseImage(epd.getbuffer(image))
        epd.init(epd.PART_UPDATE)
        while True:
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
            datetime = time.strftime("%m/%d/%y %H:%M:%S")
            print(f"FX Rate: {fx_rate} Instarem: {rate_instarem} Remitly: {rate_remitly} Xoom: {rate_xoom} Ria: {rate_ria}  Last Updated {datetime}")
            draw.rectangle([(0, 0), (epd.height, 26)], fill=255)
            draw.text((0, 0), f"$1 = {fx_rate}", font=font24, fill=0)
            draw.text((140, 2), time.strftime("%m/%d %H:%M"), font=font20, fill=0)
            draw.line([(0, 30), (epd.height, 30)], fill=0, width=1)
            rate_all = {
                "instarem": rate_instarem,
                "remitly": rate_remitly,
                "xoom": rate_xoom,
                "ria": rate_ria
                }
            rate_sorted = sorted(rate_all.items(), key=lambda x: x[1], reverse=True)
            draw.rectangle([(0, 75), (epd.height, 105)], fill=255)
            ypos_icon = 10
            ypos_rate = 0
            space_icon = 65
            for name, rate in rate_sorted:
                image.paste(get_icon(name), (ypos_icon, 40))
                if rate != 0:
                    draw.text((ypos_rate, 75), str(rate), font=font20, fill=0)
                ypos_icon += space_icon
                ypos_rate += space_icon
            draw.rectangle((0, 104, 249, 121), fill=255, outline=0)
            epd.displayPartial(epd.getbuffer(image))
            currentperf = time.time()
            try:
                diagnostics = {
                "CPU Temp": rpi.cpu_temp,
                "IP Address": rpi.ip_address,
                "Host": rpi.host_name,
                "Operating System": rpi.os_name,
                "Client Version:": cloud4rpi.__version__,
                }
                variables = {
                    "Fx Rate": {
                        "type": "numeric",
                        "value": fx_rate
                    },
                    "Instarem": {
                        "type": "numeric",
                        "value": rate_instarem
                    },
                    "Remitly": {
                        "type": "numeric",
                        "value": rate_remitly
                    },
                    "Xoom": {
                        "type": "numeric",
                        "value": rate_xoom
                    },
                    "Ria": {
                        "type": "numeric",
                        "value": rate_ria
                    }
                }
                device.declare(variables)
                device.declare_diag(diagnostics)
                # device.publish_config()
                # time.sleep(1)
                device.publish_diag()
                if currentperf - lastrun > 300:
                    print("Uploading  Data to cloud4rpi")
                    device.publish_data()
                    lastrun = time.time()
            except Exception as e:
                error = cloud4rpi.get_error_message(e)
                cloud4rpi.log.exception("ERROR! %s %s", error, sys.exc_info()[0])
            for i in range(10, 255, 10):
                draw.rectangle((0, 107, i, 118), fill=0)
                epd.displayPartial(epd.getbuffer(image))
                time.sleep(2)
    except KeyboardInterrupt:
        epd2in13_V2.epdconfig.module_exit()
        exit()


if __name__ == "__main__":
    main()
