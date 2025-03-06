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
2. Move the .MF4 file(s) from the CANEdge1's SD card to the "rawdata" subfolder. Do not change the names (i.e. make sure they are  numbered in the order the files were created).
3. Drag each of the .MF4 files over the mdf2csv.exe file and check that it has produced a .csv file with the same name.
4. Run the preprocessing.exe program and wait for it to complete.
5. Check the output csv files in the "processeddata" subfolder. A txt file with the variables recorded, number of samples, and sample rates will be saved in the same location.

To make changes to the program, open preprocessing.py in an IDE and install any missing packages.