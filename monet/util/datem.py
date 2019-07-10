# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
import numpy as np
import datetime
import os
from subprocess import call
from os import path
import sys
import os
import pandas as pd

# from ashfall_base_iceland import RunParams
# from arlhysplit.runh import date2dir


"""
NAME: datem.py
PRGRMMR: Alice Crawford ORG: NOAA ARL
ABSTRACT: Calls c2datem to extract information from HYSPLIT output files. Adds information to the c2datem output.
CTYPE: source code

FUNCTIONS
writedatem_sh : writes a shell script to run c2datem on the cdump files (HYPSLIT output binary concentration files).
                The shell script will also have lines to concatenate all the output into one text file and add extra information
                to the end of each line (infor about particle size and vertical concentration level which is originally in the file name).

writedatem : writes a datem file which tells c2datem which positions and times to extract concentrations from the cdump file for.

frame2datem(dfile, df,  header_str='Header', writeover=True,\

read_dataA : reads dt

"""


def writedatem_sh(
    cfile_list,
    mult="1e20",
    mdl="./",
    ofile_list=None,
    psizes=[1],
    zlra=[1],
    concat=True,
    concatfile="model.txt",
    add2ra=["none"],
):
    """Writes a .sh file to run the c2datem program on the HYSPLIT output files
       Writes separate file for each particle size. and vertical concentration level.
       psizes : a list of particle sizes to write (particle size indices 1..N)
       zlra   : a list of vertical concentration levels to write (indice 1..N)
       concat : concatenate all the files into one file with name specified by concatfile (model.txt is default).
                information about the particle size and vertical concentration level is added to the end of each line.
       concatfile : name of file with all the data
       add2ra : extra information to add to each line. The extra information is added using sed.
    """
    with open("datem.sh", "w") as fid:
        fid.write("#!/bin/sh \n")
        # removes any existing model.txt file
        fid.write("rm -f " + concatfile + "\n")
        fid.write("MDL=" + mdl + "\n")
        fid.write("mult=" + str(mult) + "\n")
        if ofile_list is None:
            ofile_list = []
            for cfile in cfile_list:
                ofile_list.append(cfile.replace("cdump", "model"))
        outfile_list = []
        for zl in zlra:
            fid.write("zl=" + str(zl) + "\n")
            iii = 0
            for cfile in cfile_list:
                for psz1 in psizes:
                    try:
                        psz = abs(int(psz1))
                    except BaseException:
                        psz1 = 1
                    else:  # if try does not raise an exception then this code is executed.
                        if zl == -1:
                            zstr = "zn1"
                        else:
                            zstr = ".z" + str(zl)
                        outfile = ofile_list[iii] + ".p" + str(int(psz)) + zstr + ".txt"
                        # print iii, outfile
                        outfile_list.append(outfile)
                    # Following block writes line in shell script to run c2datem
                    # the -h0 specifies to not write header lines.
                    # print('WRITING', cfile)
                    fid.write(
                        "$MDL/c2datem -n -h0 -i"
                        + cfile.strip()
                        + " -mdatemfile.txt -o"
                        + outfile
                        + "  -c$mult -z$zl"
                    )
                    # pollutant index select for multiple species
                    fid.write(" -p" + str(int(psz)))
                    fid.write("\n")
                    if concat:
                        temp = cfile.split(".")
                        if add2ra[0] != "none":
                            a2l = " " + add2ra[iii] + " " + str(psz) + " " + str(zl)
                            # add info to end of line and add to file.
                            fid.write(
                                "sed 's/$/"
                                + a2l
                                + "/' "
                                + outfile
                                + " >> "
                                + concatfile
                                + "\n"
                            )
                iii += 1
        fid.write("if [ ! -s model.txt ]\n")
        fid.write("then\n")
        fid.write("rm -f model.txt\n")
        fid.write("fi\n")

    return outfile_list


def frame2datem(
    dfile,
    df,
    header_str="Header",
    writeover=True,
    cnames=["date", "duration", "lat", "lon", "obs", "vals", "sid", "altitude"],
):
    """converts a pandas dataframe with columns names by cnames (date, duration, lat, lon, obs, vals, sid, altitude)
       to a text file in datem format.
       date should be a datetime object.
       duration should be a string format HHMM (TODO- make this more flexible?)
       lat - latitude, float
       lon - longitude, float
       obs - value of observation, float
       vals - modeled value, float
       sid  - station id, int or string
       altitude - float """
    iii = 0
    if writeover:
        with open(dfile, "w") as fid:
            fid.write(header_str + " (obs then model) " + "\n")
            fid.write(
                "year mn dy shr dur(hhmm) LAT LON  ug/m2 ug/m2 site_id  height \n"
            )
    with open(dfile, "a") as fid:
        for index, row in df.iterrows():
            fid.write(row[cnames[0]].strftime("%Y %m %d %H%M") + " ")
            fid.write(str(row[cnames[1]]) + " ")
            fid.write("%8.3f  %8.3f" % (row[cnames[2]], row[cnames[3]]))
            fid.write("%8.4f  %8.4f " % (row[cnames[4]], row[cnames[5]]))
            if isinstance(row[cnames[6]], int):
                fid.write("%12i" % (row[cnames[6]]))
            elif isinstance(row[cnames[6]], float):
                fid.write("%12i" % (row[cnames[6]]))
            elif isinstance(row[cnames[6]], str):
                fid.write("%12s  " % (row[cnames[6]]))
            else:
                print("WARNING frame2datem function: not printing station id")
            fid.write("%7.2f \n" % (row[cnames[7]]))
            # fid.write(str(row[cnames[7]]) + '\n')


def writedatem(dfile, stationlocs, sample_start, sample_end, stime, height=" 10"):
    """writes a dummy station datem file which has times for each station location.
       This file is used by c2datem to determine what concentration values to pull from the cdump files.
       stationlocs is a list of (lat,lon) tuples.

       If the -z option in c2datem is set to -1 then the height
       indicates which level will be used. It is the actual height in meters, not
       the index of the height lev
el.

       outputs 1 in the measurement concentration and sourceid columns.
    """
    iii = 0
    with open(dfile, "w") as fid:
        fid.write("DOE ASHFALL PROJECT\n")
        fid.write("year mn dy shr dur(hhmm) LAT LON g/m2  site_id  height \n")
        for iii in range(0, len(stationlocs)):
            sdate = sample_start
            while sdate < sample_end:
                fid.write(sdate.strftime("%Y %m %d %H%M") + " ")
                fid.write(str(stime[iii]) + "00 ")
                fid.write(
                    "{:0.3f}".format(stationlocs[iii][0])
                    + " "
                    + "{:0.3f}".format(stationlocs[iii][1])
                    + " "
                )
                fid.write("1 ")
                fid.write("1 ")
                # fid.write(height + '\n')
                fid.write(height + "\n")
                sdate += datetime.timedelta(hours=stime[iii])


def read_dataA(fname):
    """
    reads merged data file output by statmain.
    outputs a  dataframe with columns
    date, sid, lat, lon, obs, model
    """
    colra = ["Num", "sid", "lat", "lon", "year", "month", "day", "hour", "obs", "model"]
    dtp = {"year": int, "month": int, "day": int, "hour": int}
    datem = pd.read_csv(
        fname, names=colra, header=None, delimiter=r"\s+", dtype=dtp, skiprows=2
    )
    if not datem.empty:
        datem["minute"] = datem["hour"] % 100
        datem["hour"] = datem["hour"] / 100
        datem["hour"] = datem["hour"].astype(int)

        def getdate(x):
            return datetime.datetime(
                int(x["year"]),
                int(x["month"]),
                int(x["day"]),
                int(x["hour"]),
                int(x["minute"]),
            )

        try:
            datem["date"] = datem.apply(getdate, axis=1)
        except BaseException:
            print("EXCEPTION", fname)
            print(datem[0:10])
            sys.exit()
        datem.drop(["year", "month", "day", "hour", "minute"], axis=1, inplace=True)
    return datem


def read_datem_file(
    fname,
    dummy=False,
    verbose=False,
    colra=[
        "year",
        "month",
        "day",
        "hour",
        "duration",
        "meas_lat",
        "meas_lon",
        "vals",
        "stationid",
        "sourceid",
        "level",
        "thickness",
    ],
):
    """ Reads a datem file and returns a dataframe with colums described by colra
       colra : should have columns for 'year' 'month' 'day' 'hour'. 'hour' column should be in hhmm format.
       fname :
       zlevs :
       sdate :

       returns pandas dataframe.
    """
    dtp = {"year": int, "month": int, "day": int, "hour": int}
    datem = pd.read_csv(fname, names=colra, header=None, delimiter=r"\s+", dtype=dtp)
    datem.columns = colra
    datem["minute"] = datem["hour"] % 100
    datem["hour"] = datem["hour"] / 100
    datem["hour"] = datem["hour"].astype(int)

    def getdate(x):
        return datetime.datetime(
            int(x["year"]),
            int(x["month"]),
            int(x["day"]),
            int(x["hour"]),
            int(x["minute"]),
        )

    datem["date"] = datem.apply(getdate, axis=1)
    datem.drop(["year", "month", "day", "hour", "minute"], axis=1, inplace=True)
    return datem