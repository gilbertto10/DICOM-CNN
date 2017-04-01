#An example of a few useful things that can be done with DICOM files


from __future__ import division
import matplotlib
import matplotlib.pyplot as plt
import numpy
import dicom
import os 
import theano.tensor as T
import theano.tensor.nnet as nnet
import theano.tensor.signal.pool as pool
import theano


#This function creates a dictionary that maps patient IDs to cancer incidence
def parseLabels(labelFile):
    #Throw away header
    labelFile.readline()
    patientLabels = {}

    #Read each line and add it to the dictionary
    for line in labelFile:
        line = line.strip().split(',')
        #print(line)
        #Throw out malformed input and empty lines
        if len(line) != 2:
            continue
        patientLabels[line[0]] = line[1]
    return patientLabels


labelFile = open("./labels.csv")
idLabels = parseLabels(labelFile)

dirs = os.walk("./images")
#Skip the directory itself, only look at subdirectories
dirs.next()

#Create a list of tuples mapping 3d numpy arrays of image data to their label
for directory in dirs:
    currDir = os.path.basename(directory[0])
    patientData = []
    if currDir in idLabels:
        dataList = []
        #Add each array to a list
        for image in directory[2]:
            imageHandle = dicom.read_file(directory[0] + '/' + image)
            imgData = imageHandle.pixel_array
            dataList.append(imageHandle.pixel_array)
        
        #Preprocess all images from the patient to set a zero mean
        dataList -= numpy.mean(dataList)
    
        #Add the 3d array of all images from a patient to the list
        patientData.append((numpy.stack(dataList), idLabels[currDir]))
#PatientData = list of tuples containing (0) image matrix and (1) tag

Img = T.tensor4(name="Img")
Lab = T.dscalar()

#Layer 1
f1size = 8
numFilters1 = 5
p1Factor = 3
learnRate = .0001
#outChannels, inChannels, filterRows, filterCols
f1Arr = numpy.random.randn(numFilters1, 1, f1size ,f1size) 
F1 = theano.shared(f1Arr, name = "F1")
bias1 = numpy.random.randn()
b1 = theano.shared(bias1, name = "b1")
#Output = batches x channels x 512 - f1size x 512 - f1size
conv1 = nnet.sigmoid(nnet.conv2d(Img, F1) + b1)
pool1 = pool.pool_2d(conv1, (p1Factor,p1Factor), ignore_border = True)
layer1 = theano.function([Img], pool1)

#Layer 2
f2size = 7
numFilters2 = 10
pool2Factor = 6
f2Arr = numpy.random.randn(numFilters2, numFilters1, f2size, f2size)
F2 = theano.shared(f2Arr, name = "F2")
bias2 = numpy.random.randn()
b2 = theano.shared(bias2, name = "b2")
conv2 = nnet.sigmoid(nnet.conv2d(pool1, F2) + b2)
pool2 = pool.pool_2d(conv2, (pool2Factor,pool2Factor), ignore_border = True)
layer2 = theano.function([Img], pool2)

#Calculate the size of the output of the second convolutional layer
convOutLen = (((512 - numFilters1) //p1Factor + 1) - numFilters2) // pool2Factor + 1
convOutLen = convOutLen * convOutLen * numFilters2

#Layer 3
b3arr = numpy.random.randn()
b3 = theano.shared(b3arr, name = "b3")
w3arr = numpy.random.randn(convOutLen, convOutLen / numFilters2)
w3 = theano.shared(w3arr, name = "w3")
hidden3 = theano.dot(pool2.flatten(), w3) + b3
layer3 = theano.function([Img], hidden3)

#Layer 4
w4arr = numpy.random.randn(convOutLen / numFilters2)
w4 = theano.shared(w4arr, name = "w4")
hidden4In = nnet.sigmoid(hidden3)
hidden4 = theano.dot(hidden4In, w4)
layer4 = theano.function([Img], hidden4)

#Output layer
output = nnet.sigmoid(hidden4)

error = T.sqr(abs(output - Lab))
F1Grad = T.grad(error, F1)
F2Grad = T.grad(error, F2)
w3Grad = T.grad(error, w3)
w4Grad = T.grad(error, w4)

train = theano.function([Img, Lab], error, updates = [(F1, F1 - F1Grad * learnRate),
         (F2, F2 - F2Grad * learnRate),
         (w3, w3 - w3Grad * learnRate),
         (w4, w4 - w4Grad * learnRate)])




#Batch size, channels, rows, cols
images = patientData[0][0][1].reshape(1,1,512,512)
label = patientData[0][1]

print(label)
for i in range(100):
    print(train(images, 0))



#result = layer1(images)
#print(result[0][0].shape)
#plt.subplot(1,3,1)
#plt.imshow(patientData[0][0][1])
#plt.gray()
#plt.subplot(1,3,2)
#plt.imshow(result[0][0])
#plt.gray()
#result = layer2(images)
#print(result[0][0].shape)
#plt.subplot(1,3,3)
#plt.imshow(result[0][0])
#plt.gray()
#plt.show()
