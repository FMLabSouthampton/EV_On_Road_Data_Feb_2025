# Input: CSV file(s) containing raw data from CANEdge1. Make sure the files are numbered in the order they were created.
# Output: Merged and processed data files for speed, acceleration, and GPS data.
import os
import csv
import pandas as pd
import statistics
import time
from datetime import datetime
from tabulate import tabulate

raw_data = []

# Empty lists for data output
l_M_Torque = []  # Motor torque:    7EB, 23
l_M_RPM = []     # Motor RPM:       7EC, 28
l_HV_V = []      # Battery Voltage: 7EC, 22
l_HV_I = []      # Battery Current: 7EC, 22
l_HV_SOC = []    # Battery SoC:     7EC, 21

l_Acc_P = []     # Accel. pedal:    7EA, 21
l_Brake_P = []   # Brake pedal:     7D9, 25

l_Speed = []     # Vehicle speed:   7D9, 22
l_Acc = []       # Vehicle accel:   7D9, 21

l_gpss = []      # GPS Status:      065, N/A
l_gpsp = []      # GPS Position:    067, N/A
l_gpsa = []      # GPS Altitude:    068, N/A

# TimestampEpoch;BusChannel;ID;IDE;DLC;DataLength;Dir;EDL;BRS;ESI;RTR;DataBytes
IGNORED_KEYS = ["BusChannel", "IDE", "DLC", "DataLength", "Dir", "EDL", "BRS", "ESI", "RTR"]
INITIAL_TIMESTAMP = 0


# Reorders the cols the dictionary so it can be read by the Matlab program when imported
def fdict(data: dict) -> dict:
    data = {k: v for k, v in data.items() if k not in ["ID", "DataBytes", "TimestampEpoch"]}  # removing redundant columns
    return data


# Converting the Epoch Timestamp into a relative one.
def process_timestamp(data: dict) -> dict:
    timestamp = (float(data["TimestampEpoch"]) - INITIAL_TIMESTAMP) * 1000
    data.update({"Timestamp": str(timestamp)})
    return data


def s_rate(data: list) -> float:
    timestamp_differences = []
    for e in range(1, len(data)):
        timestamp_differences.append(int(float(data[e]["Timestamp"]) - float(data[e - 1]["Timestamp"])))
    return statistics.median(timestamp_differences) / 1000


# =-=-=-=-=-=-=-=-= Processing Functions =-=-=-=-=-=-=-=-=-=-= #
# Converting raw speed data to speed in m/s.
def process_speed(data: dict) -> dict:
    d7 = data["DataBytes"][8:10]    # getting data byte d7
    d7 = int(d7, 16) * 5/18         # converting from hex to decimal and converting units to m/s
    data.update({"Speed(m/s)": d7})
    return data


# Converting raw acceleration data to acceleration in m/s.
def process_acceleration(data: dict) -> dict:
    d17 = data["DataBytes"][14:16]                   # getting data byte d17
    d17 = (int(d17, 16) - 127) / 64 * 9.80665        # converting from hex to decimal and converting units to m/s^2
    data.update({"Acceleration(m/s^2)": d17})
    return data


# Converting raw gpsstatus data to readable FixType and Satellites.
def process_gpss(data: dict) -> dict:
    d1 = data["DataBytes"][0:2]                     # getting data byte d1
    d1 = bin(int(d1, 16))[2:].zfill(8)              # converting from hex to 8-bit binary number
    sat = int(d1[:5], 2)     # first 5 chars of the binary string converted to dec
    fix = int(d1[-3:], 2)    # last 3 chars of the binary string converted to dec
    data.update({"FixType": fix, "Satellites": sat})
    return data


# Converting raw gpsposition data to readable PositionValid, Latitude(deg), Longitude(deg), and PositionAccuracy(m)
def process_gpsp(data: dict) -> dict:
    d = [data["DataBytes"][i:i + 2] for i in range(0, 16, 2)]   # separating databytes field into individual hex values
    d = [bin(int(i, 16))[2:].zfill(8)[::-1] for i in d]         # converting each hex to binary and reversing
    d1, d2, d3, d4, d5, d6, d7, d8 = d

    pos_valid = d1[::-1][0]                         # extracting most significant bit of d1

    lat = d1[-7:] + d2 + d3 + d4[:5]                # extracting relevant portion of binary string
    lat = int(lat[::-1], 2) * 0.000001 - 90         # converting from binary to decimal and into degrees

    long = d4[-3:] + d5 + d6 + d7 + d8[:2]          # extracting relevant portion of binary string
    long = int(long[::-1], 2) * 0.000001 - 180      # converting from binary to decimal and into degrees

    acc = int(d8[-6:][::-1], 2)

    data.update({"PositionValid": pos_valid, "Latitude(deg)": lat, "Longitude(deg)": long, "PositionAccuracy(m)": acc})
    return data


# Converting raw gpsaltitude data to readable PositionValid, Altitude(m), and Accuracy(m)
def process_gpsa(data: dict) -> dict:
    d = [data["DataBytes"][i:i + 2] for i in range(0, 8, 2)]   # separating databytes field into individual hex values
    d = [bin(int(i, 16))[2:].zfill(8)[::-1] for i in d]         # converting each hex to binary and reversing
    d1, d2, d3, d4 = d

    pos_valid = d1[::-1][0]   # most significant bit of d1

    alt = d1[-7:] + d2 + d3[:3]                     # extracting relevant portion of binary string
    alt = int(alt[::-1], 2) * 0.1 - 6000            # converting from binary to decimal and into meters

    acc = d3[-5:] + d4                              # extracting relevant portion of binary string
    acc = int(acc[::-1], 2)                         # converting from binary to decimal

    data.update({"PositionValid": pos_valid, "Altitude(m)": alt, "PositionAccuracy(m)": acc})
    return data


def process_brkp(data: dict) -> dict:
    d35 = data["DataBytes"][8:10]       # getting data byte d35
    d35 = int(d35, 16) * 64/100         # converting from hex to decimal and converting into readable %
    data.update({"Brake_P(%)": d35})
    return data


def process_accp(data: dict) -> dict:
    d10 = data["DataBytes"][14:16]       # getting data byte d10
    d10 = int(d10, 16) / 2               # converting from hex to decimal and converting into readable %
    data.update({"Acc_P(%)": d10})
    return data


def process_m_torque(data: dict) -> dict:
    d22 = data["DataBytes"][10:12]              # getting data byte d22
    d23 = data["DataBytes"][12:14]              # getting data byte d23

    d22 = int(d22, 16)                          # converting to decimal

    d23 = d23.zfill(len(d23) + len(d23) % 2)    # making hex number an even length
    if d23[0] not in "01234567":                # converts from unsigned hex to signed decimal (i.e. can be negative)
        d23 = int(d23, 16) - 16 ** len(d23)
    else:
        d23 = int(d23, 16)

    torque = (d23*256 + d22)/100                # merging values and converting to Nm

    data.update({"M_Torque(Nm)": torque})
    return data


def process_m_rpm(data: dict) -> dict:
    d54 = data["DataBytes"][4:6]                # getting data byte d54
    d55 = data["DataBytes"][6:8]                # getting data byte d55

    d55 = int(d55, 16)                          # converting to decimal

    d54 = d54.zfill(len(d54) + len(d54) % 2)    # making hex number an even length
    if d54[0] not in "01234567":                # converts from unsigned hex to signed decimal (i.e. can be negative)
        d54 = int(d54, 16) - 16 ** len(d54)
    else:
        d54 = int(d54, 16)

    rpm = d54*256 + d55                         # merging values and converting to rpm

    data.update({"M_RPM(RPM)": rpm})
    return data


def process_hv_vi(data: dict) -> (dict, dict):
    data_i = data.copy()
    data_v = data.copy()
    d11 = data["DataBytes"][2:4]                # getting data byte d11
    d12 = data["DataBytes"][4:6]                # getting data byte d12
    d13 = data["DataBytes"][6:8]                # getting data byte d13
    d14 = data["DataBytes"][8:10]               # getting data byte d14

    d12 = int(d12, 16)                          # converting to decimal
    d13 = int(d13, 16)                          # converting to decimal
    d14 = int(d14, 16)                          # converting to decimal

    d11 = d11.zfill(len(d11) + len(d11) % 2)    # making hex number an even length
    if d11[0] not in "01234567":                # converts from unsigned hex to signed decimal (i.e. can be negative)
        d11 = int(d11, 16) - 16 ** len(d11)
    else:
        d11 = int(d11, 16)

    hv_i = (d11*256 + d12) / 10
    hv_v = (d13*256 + d14) / 10
    data_v.update({"HV_V(V)": hv_v})
    data_i.update({"HV_I(A)": hv_i})
    return data_v, data_i


def process_hv_soc(data: dict) -> dict:
    d5 = data["DataBytes"][4:6]                 # getting data byte d5
    d5 = int(d5, 16) / 2                        # converting from hex to decimal and into a readable percentage
    data.update({"SOC(%)": d5})
    return data


# =-=-=-=-=-=-=-=-= Main Program =-=-=-=-=-=-=-=-=-=-= #


print("Reading and unpacking input CSVs...")
# Reading the CSV files in rawdata folder, merging into a single dict, and filtering timestamp, ID, and databyte columns
for filename in os.listdir("rawdata"):
    f = os.path.join("rawdata", filename)   # getting file paths of each file in the raw data folder
    if filename.endswith(".csv"):
        print(f"Reading: {f}")
        with open(f, "r") as file:
            csv_reader = csv.DictReader(file, delimiter=";")
            for row in csv_reader:
                row = {k: v for k, v in row.items() if k not in IGNORED_KEYS}
                raw_data.append(row)
    else:
        print(f"Ignoring: {f}")
print("Finished reading.")

# Identifying the initial timestamp.
INITIAL_TIMESTAMP = float(raw_data[0]["TimestampEpoch"])
DATE_STRING = datetime.fromtimestamp(INITIAL_TIMESTAMP).strftime('%d%m%y')
print(f"Initial timestamp of dataset: {datetime.fromtimestamp(INITIAL_TIMESTAMP).strftime('%Y-%m-%d %H:%M:%S')}")

# Splitting raw data into lists of desired values depending on ID and index.
print("Beginning filtering and processing...")
for entry in raw_data:
    match str(entry["ID"]):
        case "7EC":
            if str(entry["DataBytes"])[0:2] == "28":
                l_M_RPM.append(fdict(process_m_rpm(process_timestamp(entry))))
            elif str(entry["DataBytes"])[0:2] == "22":
                v, i = process_hv_vi(process_timestamp(entry))
                l_HV_V.append(fdict(v))
                l_HV_I.append(fdict(i))
            elif str(entry["DataBytes"])[0:2] == "21":
                l_HV_SOC.append(fdict(process_hv_soc(process_timestamp(entry))))
        case "7EB":
            if str(entry["DataBytes"][0:2]) == "23":
                l_M_Torque.append(fdict(process_m_torque(process_timestamp(entry))))
        case "7EA":
            if str(entry["DataBytes"][0:2]) == "21":
                l_Acc_P.append(fdict(process_accp(process_timestamp(entry))))
        case "7D9":
            if str(entry["DataBytes"])[0:2] == "21":
                l_Speed.append(fdict(process_speed(process_timestamp(entry))))
            elif str(entry["DataBytes"])[0:2] == "22":
                l_Acc.append(fdict(process_acceleration(process_timestamp(entry))))
            elif str(entry["DataBytes"])[0:2] == "25":
                l_Brake_P.append(fdict(process_brkp(process_timestamp(entry))))
        case "065":
            l_gpss.append(fdict(process_gpss(process_timestamp(entry))))
        case "067":
            l_gpsp.append(fdict(process_gpsp(process_timestamp(entry))))
        case "068":
            l_gpsa.append(fdict(process_gpsa(process_timestamp(entry))))


# Creating export folder and writing the dicts for each metric to CSVs.
export_table = {"Acc": l_Acc, "Acc_P": l_Acc_P, "Brake_P": l_Brake_P, "HV_I": l_HV_I, "HV_SOC": l_HV_SOC, "HV_V": l_HV_V, "M_RPM": l_M_RPM, "M_Torque": l_M_Torque, "Speed": l_Speed, "GPS_Altitude": l_gpsa, "GPS_Position": l_gpsp, "GPS_Status": l_gpss}
export_folder = os.path.join("processeddata", DATE_STRING)
if os.path.exists(export_folder):   # checks if a folder has already been generated for testing on that day and creates a new one with suffix _num if true
    counter = 1
    while os.path.exists(f"{export_folder}_{counter}"):
        counter += 1
    export_folder += f"_{counter}"
os.makedirs(export_folder)       # creating the export folder

# xlsx_or_csv = input("Type 0 to export as .csv, type 1 to export as .xlsx, or type 2 to export as both. Saving as xlsx will take longer.")
for name, datas in export_table.items():
    path = os.path.join(export_folder, f"{DATE_STRING}_{name}.csv")
    fieldnames = datas[0].keys()

    with open(path, mode="w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(datas)
    '''
    if xlsx_or_csv in ["1", "2"]:
        xlsx_path = os.path.join(export_folder, f"{DATE_STRING}_{name}.xlsx")
        df = pd.read_csv(path)
        df.to_excel(xlsx_path, index=False, engine="openpyxl")
        if xlsx_or_csv == "1":
            os.remove(path)
        print(f"Saved: {xlsx_path}")
    if xlsx_or_csv in ["0", "2"]:
        print(f"Saved: {path}")'''
    print(f"Saved: {path}")


print("Calculating median sampling rates for each type...")
table = [["Speed", len(l_Speed), s_rate(l_Speed)], ["Acceleration", len(l_Acc), s_rate(l_Acc)], ["Current/Voltage", len(l_HV_V), s_rate(l_HV_V)], ["State of Charge", len(l_HV_SOC), s_rate(l_HV_SOC)], ["Accel. Pedal Position", len(l_Acc_P), s_rate(l_Acc_P)], ["Brake Pedal Position", len(l_Brake_P), s_rate(l_Brake_P)], ["Motor Torque", len(l_M_Torque), s_rate(l_M_Torque)], ["Motor RPM", len(l_M_RPM), s_rate(l_M_RPM)], ["GPS Readings", len(l_gpsp), s_rate(l_gpsp)]]
print("Total datapoints and median sample rates of each type:")
print(tabulate(table, headers=["Metric", "# of Samples", "Sample Rate (s^-1)"]))
path = os.path.join(export_folder,'output.txt')
with open(path, 'w') as f:
    f.write(tabulate(table, headers=["Metric", "# of Samples", "Sample Rate (s^-1)"]))

print("Finished processing!")
print(f"Total number of signals logged in dataset: {len(raw_data)}")
print(f"Files saved in: {export_folder}")
print(f"Saved table output to: {path}")
time.sleep(5)
