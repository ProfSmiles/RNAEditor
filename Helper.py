'''
Created on May 22, 2013

@author: david
'''

from datetime import datetime
import argparse, sys, os, subprocess, errno
from collections import defaultdict, OrderedDict
import traceback
import ui
import numpy as np
import matplotlib.pyplot as plt



class Parameters():
    '''
    Reads and saves the default values from the configuration File 'configurtion.txt'
    '''
    
    def __init__(self,source="configuration.txt"):
        '''
        creates an parameter object which contains all the parameters for RnaEditor
        :param source: either a QWidget or a textFile from where the parameters are read from
        '''
        if type(source)==str:
            self.readDefaultsFromFile(source)
        elif isinstance(source, ui.InputTab.InputTab):
            self.getParametersFromInputTab(source)
        else:
            Helper.error("Parameter source has wrong Type [str or QWidget]")
    
    
    def getParametersFromInputTab(self,inputTab):
        '''
        get the Parameters and update the default Parameters from the Default class 
        '''
        self.refGenome = str(inputTab.refGenomeTextBox.text())
        self.gtfFile = str(inputTab.gtfFileTextBox.text())
        self.dbsnp = str(inputTab.dbsnpTextBox.text())
        self.hapmap = str(inputTab.hapmapTextBox.text())
        self.omni = str(inputTab.omniTextBox.text())
        self.esp = str(inputTab.espTextBox.text())
        self.aluRegions = str(inputTab.aluRegionsTextBox.text())
        self.output = str(inputTab.outputTextBox.text())
        self.sourceDir = str(inputTab.sourceDirTextBox.text())
        
        self.threads = str(inputTab.threadsSpinBox.value())
        self.maxDiff = str(inputTab.maxDiffSpinBox.value())
        self.seedDiff = str(inputTab.seedSpinBox.value())
        self.standCall = str(inputTab.standCallSpinBox.value())
        self.standEmit = str(inputTab.standEmitSpinBox.value())
        self.edgeDistance = str(inputTab.edgeDistanceSpinBox.value())
        self.paired = inputTab.pairedCheckBox.isChecked()
        self.overwrite = inputTab.overwriteCheckBox.isChecked()
        self.keepTemp = inputTab.keepTempCheckBox.isChecked()
        
            
    def readDefaultsFromFile(self,file):
        try:
            confFile = open(file)
        except IOError:
            Helper.error("Unable to open configuration file")
        for line in confFile:
            if line.startswith("#"):
                continue
            if line == "\n":
                continue
            
            line=line.rstrip()
            id, value = line.split("=")
            id=id.strip()
            value=value.strip()

            if id=="refGenome":
                self.refGenome=value
            elif id=="dbSNP":
                self.dbsnp=value
            elif id=="hapmap":
                self.hapmap=value
            elif id=="omni":
                self.omni=value
            elif id=="esp":
                self.esp=value
            elif id == "aluRegions":
                self.aluRegions=value
            elif id == "gtfFile":
                self.gtfFile=value
            elif id == "output":
                self.output=value
            elif id == "sourceDir":
                self.sourceDir=value
            elif id == "maxDiff":
                self.maxDiff=str(value)
            elif id == "seedDiff":
                self.seedDiff=str(value)
            elif id == "paired":
                #Parameters.paired=float(value)
                if str(value).lower() in ("yes", "y", "true",  "t", "1"): self.paired = True
                if str(value).lower() in ("no",  "n", "false", "f", "0", "0.0", "", "none", "[]", "{}"): self.paired=False
            elif id == "standCall":
                self.standCall=str(value)
            elif id == "standEmit":
                self.standEmit=str(value)    
            elif id == "edgeDistance":
                self.edgeDistance=str(value)
            elif id == "threads":
                self.threads=str(value)
            elif id == "keepTemp":
                #Parameters.paired=float(value)
                if str(value).lower() in ("yes", "y", "true",  "t", "1"): self.keepTemp = True
                if str(value).lower() in ("no",  "n", "false", "f", "0", "0.0", "", "none", "[]", "{}"): self.keepTemp=False
            elif id == "overwrite":
                #Parameters.paired=float(value)
                if str(value).lower() in ("yes", "y", "true",  "t", "1"): self.overwrite = True
                if str(value).lower() in ("no",  "n", "false", "f", "0", "0.0", "", "none", "[]", "{}"): self.overwrite=False
                

           
class Helper():
    '''
    Helpfunctions
    '''
    
    '''
    check if given directory is a readable directory and give the right data type 
    '''
    
    prefix = "*** "
    praefix = " ***"
    
    #dummy element is added to the array to avoid 0/1 problem from the Tab array and these arrays
    #otherwise i had to add -1 every time i want to access the following arrays
    runningThreads=["dummy"]

    
    
    @staticmethod
    def getSampleName(fq):
                #get name from input File
        if fq.endswith(".fastq"):
            sampleName = fq[fq.rfind("/")+1:fq.rfind(".fastq")]
        elif fq.endswith(".fq"):
            sampleName = fq[fq.rfind("/")+1:fq.rfind(".fq")]
        elif fq.endswith(".bam"):
            sampleName = fq[fq.rfind("/")+1:fq.rfind(".bam")]
        else:
            return None
        return sampleName
    
    @staticmethod
    def readable_dir(prospective_dir):
        if not os.path.isdir(prospective_dir):
            raise argparse.ArgumentTypeError("readable_dir:{0} is not a valid path".format(prospective_dir))
        if os.access(prospective_dir, os.R_OK):
            return prospective_dir
        else:
            raise argparse.ArgumentTypeError("readable_dir:{0} is not a readable dir".format(prospective_dir))
    

    @staticmethod
    def getTime():
        '''
        return current time
        '''
        curr_time = datetime.now()
        #return "["+curr_time.strftime("%c")+"]"
        return curr_time
    
    
    @staticmethod
    def convertPhred64toPhred33(fastqFile,outFile,logFile,textField):
        """
        converts the inputFile to phred33 Quality and writes it into the ourdir
        """
        startTime=Helper.getTime()
        Helper.info("[" + startTime.strftime("%c") + "] * * * convert Quality encoding: " + fastqFile[fastqFile.rfind("/")+1:]   + " * * *",logFile,textField)
        
        
        if os.path.exists(outFile):
            Helper.info("* * * [Skipping] Result File already exists * * *",logFile,textField)
            return outFile
        
        outFile = open(outFile,"w")
        fastqFile=open(fastqFile,"r")
        
        lineNumber = 0 
        for line in fastqFile:
            lineNumber+=1
            if lineNumber%4==0:
                a=[]
                for char in line.rstrip():
                    phredQual=ord(char)-64
                    phredChar=chr(phredQual+33)
                    a.append(phredChar)
                outFile.write("".join(a) + "\n")
            else:
                outFile.write(line)
        outFile.close()
        return outFile.name
    
    @staticmethod
    def isPhred33Encoding(inFastqFile,lines,logFile, runNumber):
        """
        check in the first lines if the quality encoding is phred33
        """
        fastqFile=open(inFastqFile,"r")
        lineNumber=0
        lines=lines*4
        for line in fastqFile:
            lineNumber+=1
            if lineNumber%4==0:
                for char in line.rstrip():
                    if ord(char)>74 and ord(char)<105:
                        #print line.rstrip()
                        fastqFile.close()
                        return False
                    if ord(char)>105:
                        Helper.error("%s has no valid quality encoding. \n\t Please use a valid FastQ file??" % fastqFile.name,logFile, runNumber)
            if lineNumber > lines:
                fastqFile.close()
                return True
            
        Helper.error("%s has less than %i Sequences. \n These are not enough reads for editing detection!!" % (fastqFile.name,lines),logFile, runNumber)
    
    @staticmethod
    def proceedCommand(description,cmd,infile,outfile,rnaEdit):
        '''
        run a specific NGS-processing-step on the system
        '''
        logFile=rnaEdit.logFile
        textField=rnaEdit.textField
        overwrite=rnaEdit.params.overwrite
        
        startTime=Helper.getTime()
        Helper.info("[" + startTime.strftime("%c") + "] * * * " + description + " * * *",logFile,textField)
        
        
        #check if infile exists
        if not os.path.isfile(infile):
            Helper.error(infile + "does not exist, Error in previous Step",logFile,textField)
            #Exception(infile + "does not exist, Error in previous Step")
            #exit(1)
        
        #check if outfile already exists
        
        if not os.path.isfile(outfile) or overwrite==True:
            if outfile == "None":
                resultFile=None
            else:
                resultFile=open(outfile,"w+")
            try:    
                
                #print " ".join(cmd),resultFile,logFile
                
                #retcode = subprocess.call(cmd, stdout=resultFile, stderr=logFile)
                rnaEdit.runningCommand = subprocess.Popen(cmd, stdout=resultFile, stderr=logFile)
                retcode = rnaEdit.runningCommand.wait()
                """while retcode==None:
                    #print "check if process is still running"
                    sleep(10)
                    retcode=Helper.runningCommand[runNumber].wait()
                """
                #print retcode
                
                #del Helper.runningCommand[runNumber]
                rnaEdit.runningCommand=False
                if retcode != 0:
                    if retcode == -9:
                        Helper.error(description+ " canceled by User!!!",logFile,textField)
                    else:
                        Helper.error(description+ " failed!!!",logFile,textField)
                    
                    if resultFile!=None:
                        os.remove(resultFile.name)
                    #exit(1)
            except OSError, o:
                if o.errno == errno.ENOTDIR or o.errno == errno.ENOENT:
                    Helper.error(cmd[0] + " Command not found on this system",logFile,textField)
                    if resultFile!=None:
                        os.remove(resultFile.name)
                    #exit(1)
                else:
                    Helper.error(cmd[0] + o.strerror,logFile,textField)
                    if resultFile!=None:
                        os.remove(resultFile.name)
                    #exit(1)
            Helper.printTimeDiff(startTime, logFile, textField)
        else:
            print "\t [SKIP] File already exist",logFile,textField

    @staticmethod
    def getPositionDictFromVcfFile(vcfFile,runNumber):
        """
        return a dictionary whith chromosome as keys and a set of variants as values
        variantDict={chromosome:(variantPos1,variantPos2,....)}
        """
        variantFile=open(vcfFile)
        variantDict=defaultdict(set)
        Helper.info("reading Variants from %s" % vcfFile,runNumber)
        for line in variantFile:
            #skip comments
            if line.startswith("#"): continue
            line=line.split("\t")
            chromosome,position,ref,alt = line[0],line[1],line[3],line[4]
            variantDict[chromosome].add(position)
        return variantDict
    
    @staticmethod
    def removeVariantsAFromVariantsB(variantsDictA,variantsDictB):        
        if type(variantsDictA) is str:
            variantsDictA = Helper.returnVariantDictFromVcfFile(variantsDictA)
        if type(variantsDictB) is str:
            variantsDictB = Helper.returnVariantDictFromVcfFile(variantsDictB)
            
        resultDict = defaultdict(set)
        for variant in variantsDictB.iterkeys():
            if variant not in variantsDictA[chr]:
                resultDict[chr].append(variant)
        return resultDict
       
    @staticmethod
    def returnVariantDictFromVcfFile(vcfFile):
        """
        returns the vcfFile as a two instance dictionary with chromosome as first key and a Tuple of (position,ref,alt) as second key  and  the rest of the vcfLine as a list
        {chr1: {(position1, 'A', 'G'): [dbSNP_id, ' quality', 'filter', 'attributes'], (4, 324, 'dsgdf', 'dsfsd'): [42, 243, 324]}})
        """
        vcfFile=open(vcfFile)
        vcfDict = defaultdict(dict)
        for line in vcfFile:
            #skip comments
            if line.startswith("#"): continue
            line=line.rstrip().split("\t")
            chromosome,position,ref, alt = line[0],line[1], line[3], line[4]
            vcfDict[chromosome][position,ref,alt]=([line[2]]+line[5:])
        return vcfDict



    @staticmethod
    def getCommandOutput(command):
        #print command
        #print os.path.dirname(os.path.abspath(__file__))
        #print os.getcwd()
        return subprocess.check_output(command)
    
    @staticmethod
    def countOccurrences(inFile,column=0,logFile=None,textField=0):
        '''
        Counts how often a value appears in the given column
        :param file: 
        :param column: hold the data wich should be counted
        '''
        if type(column)!=int:
            column=int(column)
        if type(inFile) == str:
            try:
                inFile=open(inFile)
            except IOError:
                Helper.warning("Could not open %s to write Variant" % file ,logFile,textField)
        if type(inFile) != file:   
            raise AttributeError("Invalid file type in 'countOccurrences' (need string or file, %s found)" % type(inFile))
        
        keySet=()
        countDict={}
        
        for line in inFile:
            if line.startswith("#"):
                continue
            value=line.split()[column]
            if value in keySet:
                countDict[value]+=1
            else:
                keySet+=(value,)
                countDict[value]=1
        
        return countDict
    
    @staticmethod    
    def createDiagramms(output,logFile=None,textField=0):
        '''
        writes all the diagrams wich aree then showd in the resultTab
        :param output: output variable of Params.putput
        '''
        
        #################################################
        ####               Basecount Plot            ####
        #################################################
        outdir = output[0:output.rfind("/")+1]
        sampleName=output[output.rfind("/"):]
        
        ind = np.arange(12)  # the x locations for the groups
        width = 0.35       # the width of the bars
        fig, ax = plt.subplots()
        
        counts1=Helper.getMMBaseCounts(output+".alu.vcf")
        rects1 = ax.bar(ind, counts1.values(), width, color='y', )
        
        counts2=Helper.getMMBaseCounts(output+".nonAlu.vcf") 
        rects2 = ax.bar(ind+width, counts2.values(), width, color='b', )
        
        # add some text for labels, title and axes ticks
        ax.set_title('Variants per Base')
        ax.set_ylabel('Number')
        ax.set_xticks(ind+width)
        ax.set_xticklabels( counts1.keys() )
        ax.legend( (rects1[0], rects2[0]), ('Alu', 'nonAlu') )
        
        def autolabel(rects):# attach some text labels
            for rect in rects:
                height = rect.get_height()
                ax.text(rect.get_x()+rect.get_width()/2., 1.05*height, '%d'%int(height), ha='center', va='bottom', fontsize=9)
        autolabel(rects1);autolabel(rects2)
        
        fig.savefig(outdir+"html/"+sampleName+"_baseCounts.png")
    
        #################################################
        ####       Editing per Position Plot         ####
        #################################################
        ind = np.arange(6)  # the x locations for the groups
        width = 0.35       # the width of the bars
        fig, ax = plt.subplots()
        
        def getPercentage(list):
            array=[]
            summe=float(sum(list))
            for value in list:
                array.append(round((float(value)/summe)*100.0,2))
            print array    
            return array
        
        counts1=Helper.countOccurrences(output+".editingSites.alu.gvf", 2, logFile, textField)
        rects1 = ax.bar(ind, getPercentage(counts1.values()), width, color='y', )
        counts2=Helper.countOccurrences(output+".editingSites.nonAlu.gvf", 2, logFile, textField) 
        rects2 = ax.bar(ind+width, getPercentage(counts2.values()), width, color='b', )
        
        ax.set_title('Editing Sites per position')
        ax.set_ylabel('Percentage')
        ax.set_ylim(0,100)
        ax.set_xticks(ind+width)
        ax.set_xticklabels( (counts1.keys()) )
        ax.legend( (rects1[0], rects2[0]), ('Alu', 'nonAlu') )
        def autolabelFloat(rects):# attach some text labels
            for rect in rects:
                height = rect.get_height()
                ax.text(rect.get_x()+rect.get_width()/2., 1.05*height, '%1.1f'%float(height), ha='center', va='bottom', fontsize=9)
        autolabelFloat(rects1);autolabelFloat(rects2)
        fig.savefig(outdir+"html/"+sampleName+"_EditingPosition.png")
        
    @staticmethod
    def printResultPage(output):
        '''
        print the HTML file wich is shown when rnaEditor is finished
        :param output: output prefix from rnaEdit object
        '''
        
        
        
        
        htmlFile = open(output+".html","w+")
        
        htmlFile.write("<html>")
        
        
        
        htmlFile.write("</html>")
    
    @staticmethod
    def getMMBaseCounts(inFile):
        '''
        Count the number of base mismatches and return the Dictionary with the numbers
        :param vcf File:
        '''
        if type(inFile) == str:
            if os.path.getsize(inFile) == 0: #getsize raises OSError if file is not existing
                raise IOError("%s File is empty" % inFile)
            inFile = open(inFile,"r")
        elif type(inFile) != file:
            raise TypeError("Invalid type in 'parseVcfFile' (need string or file, %s found)" % type(inFile)) 
        
        mmBaseCounts=OrderedDict([("A->C",0),("A->G",0),("A->T",0),("C->A",0),("C->G",0),("C->T",0),("G->A",0),("G->C",0),("G->T",0),("T->A",0),("T->C",0),("T->G",0)])
        
        for line in inFile:
            if line.startswith('#'): continue
            line=line.split()
            if line[3]=="A" and line[4]=="C": mmBaseCounts["A->C"]+=1
            elif line[3]=="A" and line[4]=="G": mmBaseCounts["A->G"]+=1
            elif line[3]=="A" and line[4]=="T": mmBaseCounts["A->T"]+=1
            elif line[3]=="C" and line[4]=="A": mmBaseCounts["C->A"]+=1
            elif line[3]=="C" and line[4]=="G": mmBaseCounts["C->G"]+=1
            elif line[3]=="C" and line[4]=="T": mmBaseCounts["C->T"]+=1
            elif line[3]=="G" and line[4]=="A": mmBaseCounts["G->A"]+=1
            elif line[3]=="G" and line[4]=="C": mmBaseCounts["G->C"]+=1
            elif line[3]=="G" and line[4]=="T": mmBaseCounts["G->T"]+=1
            elif line[3]=="T" and line[4]=="A": mmBaseCounts["T->A"]+=1
            elif line[3]=="T" and line[4]=="C": mmBaseCounts["T->C"]+=1
            elif line[3]=="T" and line[4]=="G": mmBaseCounts["T->G"]+=1
            
        return mmBaseCounts
        
    
    @staticmethod
    def printTimeDiff(startTime,logFile=None,textField=0):
        duration = Helper.getTime() - startTime
        if textField!=0:
            #currentAssay = Helper.runningAssays[textField] 
            textField.append("\t" + Helper.prefix + "[DONE] Duration [" + str(duration) + "]"  + Helper.praefix)
        if logFile!=None:
            logFile.write("\t" + Helper.prefix + "[DONE] Duration [" + str(duration) + "]"  + Helper.praefix + "\n")
        
        sys.stderr.write("\t" + Helper.prefix + "[DONE] Duration [" + str(duration) + "]"  + Helper.praefix + "\n")
    @staticmethod
    def newline (quantity=1,logFile=None,textField=0):
        if textField!=0:
            #currentAssay = Helper.runningAssays[runNumber] 
            textField.append("\n"*quantity)
        if logFile!=None:
            logFile.write("\n"*quantity)
        sys.stderr.write("\n"*quantity)
    @staticmethod
    def info (message,logFile=None,textField=0):
        if textField!=0:
            #currentAssay = Helper.runningAssays[runNumber] 
            textField.append(Helper.prefix + "INFO:    "  + message + Helper.praefix)
        if logFile!=None:
            logFile.write(Helper.prefix + "INFO:    "  + message + Helper.praefix + "\n")
        sys.stderr.write(Helper.prefix + "INFO:    "  + message + Helper.praefix + "\n")
    @staticmethod
    def warning (message,logFile=None,textField=0):
        if textField!=0:
            textField.append("\n\n" + Helper.prefix + "WARNING:    " + message + Helper.praefix + "\n\n")
        if logFile!=None:
            logFile.write(Helper.prefix + "WARNING:    "  + message + Helper.praefix + "\n")
        sys.stderr.write("\n\n" + Helper.prefix + "WARNING:    " + message + Helper.praefix + "\n\n")
    @staticmethod
    def error (message,logFile=None,textField=0):
        if textField!=0:
            textField.append("\n\n" + Helper.prefix + "ERROR:    "  + message + Helper.praefix + "\n\n")
        if logFile!=None:
            logFile.write(Helper.prefix + "ERROR:    "  + message + Helper.praefix + "\n")
        print(traceback.format_exc())
        #sys.stderr.write("\n\n" + Helper.prefix + "ERROR:    " + message + Helper.praefix + "\n\n")
        raise Exception("\n\n" + Helper.prefix + "ERROR:    " + message + Helper.praefix + "\n\n")
    @staticmethod
    def debug (message,logFile=None,textField=0):
        if textField!=0:
            textField.append(Helper.prefix + "DEBUG:    "  + message + Helper.praefix)
        if logFile!=None:
            logFile.write(Helper.prefix + "DEBUG:    "  + message + Helper.praefix + "\n")
        sys.stderr.write(Helper.prefix + message + Helper.praefix + "\n")
    @staticmethod
    def status(message,logFile=None,textField=0):
        if textField!=0:
            #currentAssay = Helper.runningAssays[runNumber] 
            textField.append(Helper.prefix + "STATUS:    "  + message + Helper.praefix)
        if logFile!=None:
            logFile.write(Helper.prefix + "STATUS:    "  + message + Helper.praefix + "\n")
        sys.stdout.write("\r" + Helper.prefix + "STATUS:    "  + message + Helper.praefix + "\n")
        sys.stdout.flush()