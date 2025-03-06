# CANEdge1 Data Processing Program
This program processes data from the CANEdge1 device collected during experiments with the Future Mobility Lab's 2023 Kia Niro EV. It converts .MF4 measurement data into processed and usable .csv files containing information on the vehicle's:
* Acceleration (m/s<sup>2</sup>)
* Speed (m/s)
* Motor RPM (RPM)
* Motor Torque (Nm)
* Battery Current (A)
* Battery Voltage (V)
* Battery State of Charge (%)
* Accelerator Pedal Position (%)
* Brake Pedal Position (%)
* GPS Status
* GPS Position (deg)
* GPS Altitude (m)
## Usage
1. Download and unzip the folder. 
2. Move the .MF4 file(s) from the CANEdge1's SD card to the "rawdata" subfolder.
3. Drag the mdf2csv.exe file over each of the .MF4 files and check that it has produced a .csv file with the same name.
4. Make sure Python is installed and then use pip to install the "tabulate" and "pandas" packages.
5. Open the preprocessing.py program.
6. Run the program.
7. Watch the terminal to make sure the process completes successfully. Once complete, information on the number of samples and the sample rates for each variable can be found in a table.
8. Collect processed csv files from the "processeddata" subfolder.