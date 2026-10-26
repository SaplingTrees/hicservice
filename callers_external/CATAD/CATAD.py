#! /usr/bin/env python3

import numpy as np
import pandas as pd
import scipy.stats as stats
import portion as p
import sys



input_path=sys.argv[1]
CS_threshold=float(sys.argv[2])
output_path=sys.argv[3]



def do_kmeans(dataSet,k):
    m=np.shape(dataSet)[0]
    #clusterAssment=np.mat(np.zeros((m,2)))
    clusterAssment=np.asmatrix(np.zeros((m,2))) # changed this because newer numpy
    clusterChange=True
    centroids=np.zeros(k)
    for i in range(k):
        centroids[i]=np.percentile(np.sort(dataSet),(((i+i+1)*100)/(k*2)))
    while clusterChange:
        clusterChange=False
        for i in range(m):
            minDist=float('inf')
            minIndex=-1
            for j in range(k):
                distance=abs(centroids[j]- dataSet[i])
                if distance<minDist:
                    minDist=distance
                    minIndex=j
                    clusterAssment[i,1]=centroids[j]
            if clusterAssment[i,0] != minIndex:
                clusterChange=True
                clusterAssment[i,0]=minIndex
        for j in range(k):
            pointInCluster = dataSet[np.nonzero(clusterAssment[:,0].A==j)[0]]
            if len(pointInCluster) !=0:
                centroids[j] = np.mean(pointInCluster,axis=0)
    return clusterAssment



def IQR_detection(lst,k):
    Q1=np.percentile(lst,25)
    Q3=np.percentile(lst,75)
    IQR=Q3-Q1
    l=[]
    index_lst=[]
    count=-1
    for i in lst:
        count+=1
        if i<Q1-IQR*k or i>Q3+IQR*k:
            l.append(i)
        else:
            index_lst.append(count)
    Lst=[x for x in lst if x not in l]
    return Lst,l,index_lst



def CS_calculate(x,y):
    assert len(x)==len(y),"len(x)!=len(y)"
    zero_lst=[0]*len(x)
    if x == zero_lst or y== zero_lst:
        return float(1) if x==y else float(0)
    res=np.array([[x[i]*y[i],x[i]*x[i],y[i]*y[i]] for i in range(len(x))])
    cos=sum(res[:,0])/(np.sqrt(sum(res[:,1]))*np.sqrt(sum(res[:,2])))
    return cos



def Cosine_Similarity(a,b,df,M):
    region1=[df.iloc[:,0][a]-1,df.iloc[:,1][a]-1]
    region2=[df.iloc[:,0][b]-1,df.iloc[:,1][b]-1]
    vector1=[]
    vector2=[]
    for i in range(len(df)):
        if i!=a and i!=b:
            feature_region=[df.iloc[:,0][i]-1,df.iloc[:,1][i]-1]
            ave_contact1=np.mean(M[region1[0]:region1[-1]+1,feature_region[0]:feature_region[-1]+1])/np.mean(M[region1[0]:region1[-1]+1,region1[0]:region1[-1]+1])
            ave_contact2=np.mean(M[region2[0]:region2[-1]+1,feature_region[0]:feature_region[-1]+1])/np.mean(M[region2[0]:region2[-1]+1,region2[0]:region2[-1]+1])
            vector1.append(ave_contact1)
            vector2.append(ave_contact2)
    CS=CS_calculate(vector1,vector2)
    return CS



def intensity_detection(matrix, up, down):
    length = len(matrix)
    region_length = down - up + 1
    if up - region_length < 0:
        surrounding_intensity = []
        if down + region_length <= length:
            d1 = np.mean(matrix[down + 1:down + 1 + region_length, down + 1:down + 1 + region_length].flatten())
            v1 = np.mean(matrix[up:down + 1, down + 1:down + 1 + region_length].flatten())
            surrounding_intensity.append(d1)
            surrounding_intensity.append(v1)
        else:
            pass
    elif down + region_length > length:
        surrounding_intensity = []
        if up - region_length >= 0:
            d1 = np.mean(matrix[up - region_length:up, up - region_length:up].flatten())
            v1 = np.mean(matrix[up - region_length:up, up:down + 1].flatten())
            surrounding_intensity.append(d1)
            surrounding_intensity.append(v1)
        else:
            pass
    else:
        surrounding_intensity = []
        d1 = np.mean(matrix[up - region_length:up, up - region_length:up].flatten())
        d2 = np.mean(matrix[down + 1:down + 1 + region_length, down + 1:down + 1 + region_length].flatten())
        v1 = np.mean(matrix[up - region_length:up, up:down + 1].flatten())
        v2 = np.mean(matrix[up:down + 1, down + 1:down + 1 + region_length].flatten())
        d3 = np.mean(matrix[up - region_length:up, down + 1:down + 1 + region_length].flatten())
        surrounding_intensity.append(d1)
        surrounding_intensity.append(d2)
        surrounding_intensity.append(v1)
        surrounding_intensity.append(v1)
        surrounding_intensity.append(d3)
    region_ave_contact = np.mean(matrix[up:down + 1, up:down + 1])
    count = 0
    for i in surrounding_intensity:
        count += 1
        if region_ave_contact <= i:
            return False
            break
        elif count == len(surrounding_intensity):
            return True
        else:
            continue



def segmentation(matrix,bin,up,down):
    min=sum(matrix[up,up:down+1])
    bin_s=up
    for i in range(up+1,down+1):
        temp=sum(matrix[i,up:down+1])
        if temp<min:
            min=temp
            bin_s=i
    if bin_s==bin:
        return []
    elif bin_s>bin:
        return [up,bin_s-1]
    else:
        return [bin_s+1,down]



def boundary_location(core1,core2,M,valid_lst):
    data=M[core1[0]:core2[-1]+1,core1[0]:core2[-1]+1]
    candidate_B=list(range(core1[-1]+1,core2[0]))
    core1_lst=list(range(core1[0],core1[-1]+1))
    core2_lst=list(range(core2[0],core2[-1]+1))
    if len(np.flatnonzero(data[len(core1_lst):len(data)-len(core2_lst)]))>0:
        ave_contact=np.sum(data[len(core1_lst):len(data)-len(core2_lst)])/len(np.flatnonzero(data[len(core1_lst):len(data)-len(core2_lst)]))
    else:
        ave_contact=0
    data=data-ave_contact
    data=np.maximum(data,0)
    remove_lst=[]
    for i in list(range(core1[-1]+1,core2[0])):
        if i not in valid_lst or data[i-core1[-1]-1].any()==False:
            remove_lst.append(i-core1[-1]-1)
            candidate_B.remove(i)
    data=np.delete(data,remove_lst,axis=0)
    data=np.delete(data,remove_lst,axis=1)
    between_core={}
    if len(np.flatnonzero(data[:len(core1_lst),len(core1_lst):len(data)]))>0:
        between_core[core1[-1]]=np.sum(data[:len(core1_lst),len(core1_lst):len(data)])/len(np.flatnonzero(data[:len(core1_lst),len(core1_lst):len(data)]))
    else:
        between_core[core1[-1]]=0
    for i in candidate_B:
        if len(np.flatnonzero(data[:len(core1_lst)+candidate_B.index(i)+1,len(core1_lst)+candidate_B.index(i)+1:len(data)]))>0:
            between_core[i]=np.sum(data[:len(core1_lst)+candidate_B.index(i)+1,len(core1_lst)+candidate_B.index(i)+1:len(data)])/len(np.flatnonzero(data[:len(core1_lst)+candidate_B.index(i)+1,len(core1_lst)+candidate_B.index(i)+1:len(data)]))
        else:
            between_core[i]=0
    up_boundary=min(between_core,key=between_core.get)
    up_index=list(between_core.keys()).index(up_boundary)
    if  up_index<len(between_core)-1:
        down_boundary=list(between_core.keys())[up_index+1]
    else:
        down_boundary=core2[0]
    between_core=sorted(between_core.items())
    return up_boundary,down_boundary,between_core



######   Highly interacted region identified based on a K-means clustering method

data=np.loadtxt(input_path)
datadig0=data.copy()
for i in range(len(data)):
    datadig0[i][i]=0
data=datadig0


km=2
List_number={}
Index_store={}
high_cluster={}

for i in range(data.shape[0]):
    List_row=[]
    for j in range(data.shape[1]):
        if data[i][j] !=0:
            List_row.append(data[i][j])
            Index_store[i]=Index_store.get(i,[])
            Index_store[i].append([i,j])
    List_number[i]=List_row
    array_row=np.array(List_row)
    if array_row[np.nonzero(array_row)].size ==0:
        pass
    else:
        clusterAssment = do_kmeans(array_row,km)
        for tmp in np.where(clusterAssment[:,0]==km-1)[0]:
            high_cluster[i]=high_cluster.get(i,[])
            high_cluster[i].append(Index_store[i][tmp])

high_cluster_df=pd.DataFrame(pd.Series(high_cluster),columns=['high_cluster'])
high_cluster_df=high_cluster_df.reset_index().rename(columns={'index':'binA'})



######   Identify pre-cores based on local density

binA=high_cluster_df['binA'].values.tolist()
High_lst=high_cluster_df['high_cluster'].values.tolist()
new_binA=[]
highbin_Per=[]
new_high_cluster=[]


for bin in binA:
    index=binA.index(bin)
    high_lst=High_lst[index]
    high_lst=IQR_detection([x[1] for x in high_lst],3)[0]
    up=high_lst[0]
    down=high_lst[-1]
    if bin>=up and bin<=down:
        new_binA.append(bin)
        per=len(high_lst)/(down-up+1)
        highbin_Per.append(per)
        new_high_cluster.append([[bin,x] for x in high_lst])

df_intensity=pd.DataFrame({'binA':new_binA,'highbin_percentage':highbin_Per,'high_cluster':new_high_cluster})
average_contact=np.sum(data)/len(np.flatnonzero(data))
High_lst=df_intensity['high_cluster'].values.tolist()
binA=df_intensity['binA'].values.tolist()
core={}
validHighlst_binA=binA.copy()

for bin in binA:
    index=binA.index(bin)
    high_lst=High_lst[index]
    up=high_lst[0][1]
    down=high_lst[-1][1]
    if np.mean(data[bin:bin+1,up:down+1])<average_contact:
        validHighlst_binA.remove(bin)
        continue
    else:
        while intensity_detection(data,up,down)==False:
            new_highregion=segmentation(data,bin,up,down)
            if new_highregion:
                up=new_highregion[0]
                down=new_highregion[-1]
            else:
                break
        if intensity_detection(data,up,down)==True:
            core[bin]=[up,down]

precore_region_df=pd.DataFrame(pd.Series(core),columns=['precore_region'])
precore_region_df=precore_region_df.reset_index().rename(columns={'index':'binA'})

precore_lst=[]
region_lst=precore_region_df['precore_region'].values.tolist()
region_lst=sorted(region_lst)

for temp in region_lst:
    if temp not in precore_lst:
        precore_lst.append([temp[0],temp[-1]])

precore_lst=[[pc[0]+1,pc[-1]+1] for pc in precore_lst]



######   Generating non-overalpping pre-cores

run=True
while(run):
    new_lst=[]
    row=0
    while (row<len(precore_lst)):
        if row==len(precore_lst)-1:
            new_lst.append(precore_lst[row])
        else:
            UPleft=precore_lst[row][0]
            UPright=precore_lst[row][-1]
            DOWNleft=precore_lst[row+1][0]
            DOWNright=precore_lst[row+1][-1]
            interval_1=p.closed(UPleft,UPright)
            interval_2=p.closed(DOWNleft,DOWNright)
            if interval_1 & interval_2==p.empty():
                new_lst.append([UPleft,UPright])
                row=row+1
                continue
            elif interval_1 in interval_2:
                new_lst.append([UPleft,UPright])
            elif interval_2 in interval_1:
                new_lst.append([DOWNleft,DOWNright])
            else:
                if intensity_detection(data,UPleft-1,DOWNright-1):
                    new_lst.append([UPleft,DOWNright])
                else:
                    ave_contact_1=np.mean(data[UPleft-1:UPright,UPleft-1:UPright])
                    ave_contact_2=np.mean(data[DOWNleft-1:DOWNright,DOWNleft-1:DOWNright])
                    if ave_contact_1 >= ave_contact_2:
                        new_lst.append([UPleft,UPright])
                    else:
                        new_lst.append([DOWNleft,DOWNright])
        row=row+2
    if precore_lst==new_lst:
        run=False
    precore_lst=new_lst

nonoverlap_precore=pd.DataFrame({'left':[pc[0] for pc in precore_lst],'right':[pc[1] for pc in precore_lst]})



######   Merging pre-cores based on cosine similarity

CS_lst=[]

for i in range(len(nonoverlap_precore)-1):
    CS=Cosine_Similarity(i,i+1,nonoverlap_precore,data)
    CS_lst.append(CS)
CS_lst.append(0)
nonoverlap_precore.insert(2,'cosine_similarity',CS_lst)

row=0
core_lst=[]

while(row<len(nonoverlap_precore)):
    if row==len(nonoverlap_precore)-1:
        core_lst.append([nonoverlap_precore['left'][row],nonoverlap_precore['right'][row]])
        row+=1
    else:
        left=nonoverlap_precore['left'][row]
        right=nonoverlap_precore['right'][row]
        CS=nonoverlap_precore['cosine_similarity'][row]
        new_region=[left,right]
        while(CS>=CS_threshold):
            left2=nonoverlap_precore['left'][row+1]
            right2=nonoverlap_precore['right'][row+1]
            if np.mean(data[left2-1:right2,nonoverlap_precore['left'][row]-1:nonoverlap_precore['right'][row]])>=average_contact:
                CS=nonoverlap_precore['cosine_similarity'][row+1]
                row+=1
                new_region=[left,right2]
            else:
                break
        core_lst.append(new_region)
        row+=1



######   Identify the attachment for each core 

boundary_lst=[]

for index in range(len(core_lst)):
    if index==0:
        up_B=core_lst[index][0]-1
        for i in list(range(core_lst[index][0]-1)):
            if i in validHighlst_binA:
                up_B=i
                break
        down_B,next_up_B,between_core=boundary_location([core_lst[index][0]-1,core_lst[index][-1]-1],[core_lst[index+1][0]-1,core_lst[index+1][-1]-1],data,validHighlst_binA)
        boundary_lst.append(up_B)
        boundary_lst.append(down_B)
        boundary_lst.append(next_up_B)
    elif index==len(core_lst)-1:
        down_B=len(data)-1
        for i in list(range(len(data)-1,core_lst[index][-1]-1,-1)):
            if i in validHighlst_binA:
                down_B=i
                break
        boundary_lst.append(down_B)
    else:
        down_B,next_up_B,between_core=boundary_location([core_lst[index][0]-1,core_lst[index][-1]-1],[core_lst[index+1][0]-1,core_lst[index+1][-1]-1],data,validHighlst_binA)
        boundary_lst.append(down_B)
        boundary_lst.append(next_up_B)

tad_lst=[]

for b in range(0,len(boundary_lst),2):
    up=boundary_lst[b]
    down=boundary_lst[b+1]
    if np.mean(data[up:down+1,up:down+1])>=average_contact:
        tad_lst.append([up,down])

with open(output_path,'w') as f:
    for i in tad_lst:
        f.write(str(i[0]+1)+'\t'+str(i[-1]+1)+'\n')



