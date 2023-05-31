# Group 3 Team Library
# group3lib.py
# DSC630 Fall 2020 - Term Project

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import scipy as sp
from scipy.spatial.distance import cdist
from scipy.spatial.distance import pdist
from sklearn.metrics import pairwise_distances
import seaborn as sns
import plotly.graph_objs as go
from sklearn.preprocessing import StandardScaler
from plotly.offline import plot
from sklearn.metrics import confusion_matrix

# Set the random seed
np.random.seed(3) 

def read_file():
    
    marketingDf = pd.read_csv("data/datasets_129450_309761_DirectMarketing.csv")
    return marketingDf

def read_file2():
    
    marketingDf = pd.read_csv("DirectMarketing1.csv")
    marketingDf.loc[marketingDf['AmountSpent'] <= 2000, 'SpendCategory'] = 'L' 
    marketingDf.loc[marketingDf['AmountSpent'] > 2000,'SpendCategory'] = 'M' 
    marketingDf.loc[marketingDf['AmountSpent'] > 4000, 'SpendCategory'] = 'H' 
    marketingDf.to_csv('DirectMarketing1_New.csv', index = False)
    return marketingDf

def create_scatterplots(data):
    
    plt.scatter(data.Salary,data.AmountSpent)
    plt.xlabel('Salary')
    plt.ylabel('Amount Spent');
    plt.title('Amount Spent vs. Salary')
    plt.show();
    
    plt.scatter(data.Catalogs,data.AmountSpent)
    plt.xlabel('Catalogs')
    plt.ylabel('Amount Spent');
    plt.title('Amount Spent vs. Catalogs')
    plt.show();
    
    plt.scatter(data.Catalogs,data.Salary)
    plt.xlabel('Catalogs')
    plt.ylabel('Salary');
    plt.title('Salary vs. Catalogs')
    plt.show();


def perform_reduction_analysis(data_df):
    # Reference code- https://scikit-learn.org/stable/auto_examples/decomposition/plot_pca_vs_lda.html#sphx-glr-auto-examples-decomposition-plot-pca-vs-lda-py
    
    data_df = data_df[['Salary', 'Children', 'Catalogs', 'Age_Middle', 'Age_Old', 'Age_Young', 'Gender_Female', 'Gender_Male', 'OwnHome_Own', 'OwnHome_Rent', 'Married_Married', 'Married_Single', 'Location_Close', 'Location_Far']]
    data_array = data_df.to_numpy()
    analysis_target = data_array[:, -1] # for last column
    target_names = ['Low Spender', 'Medium Spender', 'High_Spender']

    # Get all columns except last
    data_array = data_array[:,:-1]   
    
    X = data_array
    y = analysis_target
    #y = y.astype('int')
    pca = PCA(n_components=4)
    #X_r = pca.fit(X).transform(X)
    X_r = pca.fit_transform(X)
    
    print('X_r', X_r)
    
    data_df['pc_1'] = X_r[:,0] # sets this first principal component
    data_df['pc_2'] = X_r[:,1] # sets this second principal component
    '''
    hof_low_pc = data_analysis[(data_analysis['inducted_val']==1) & (data_analysis['pc_1']<2000)]
    print('hof_low_pc:', hof_low_pc.shape)
    
    non_hof_high_pc = data_analysis[(data_analysis['inducted_val']==0) & ((data_analysis['pc_1']> 9000) | (data_analysis['pc_2'] > 750) | (data_analysis['pc_2'] < -5000))]
    print('non_hof_high_pc:', non_hof_high_pc.shape)
    
    print("\nSaving PCA Analysis data pcaAnalysisData.xlsx \n")
    writer = pd.ExcelWriter("pcaAnalysisData.xlsx")
    data_analysis.to_excel(writer, "analysis")
    writer.save()
    
    print("\nSaving PCA Hall of Fame Outliers pcaHallOfFameOutliers.xlsx \n")
    writer = pd.ExcelWriter("pcaHallOfFameOutliers.xlsx")
    hof_low_pc.to_excel(writer, "analysis")
    writer.save()
    
    print("\nSaving PCA Non-Hall of Fame Outliers pcaNonHallOfFameOutliers.xlsx \n")
    writer = pd.ExcelWriter("pcaNonHallOfFameOutliers.xlsx")
    non_hof_high_pc.to_excel(writer, "analysis")
    writer.save()
    '''
    #lda = LinearDiscriminantAnalysis()
    #X_r2 = lda.fit(X, y).transform(X)
    
    # Percentage of variance explained for each components
    print('explained variance ratio (first two components): %s'
          % str(pca.explained_variance_ratio_))
    
    plt.figure()
    colors = ['navy', 'turquoise']
    lw = 2
    
    for color, i, target_name in zip(colors, [0, 1], target_names):
        plt.scatter(X_r[y == i, 0], X_r[y == i, 1], color=color, alpha=.8, lw=lw,
                    label=target_name)
    plt.legend(loc='best', shadow=False, scatterpoints=1)
    plt.title('PCA of dataset')
    

    plt.show()
    #return hof_low_pc, non_hof_high_pc
    
    
    #Method to plot the gap
def plot_gap(gap, k_max):
    
    plt.clf()   #clear the plot
    plt.plot(range(1, k_max+1), gap, '-o')
    plt.ylabel('gap')
    plt.xlabel('k')
    plt.savefig('Plot-Gap.pdf')
    plt.show()


#Method to plot the inertia
def plot_inertia(reference_inertia, ondata_inertia, k_max):    

    plt.clf()#clear the plot
    plt.plot(range(1, k_max+1), reference_inertia,
             '-o', label='reference')
    plt.plot(range(1, k_max+1), ondata_inertia,
             '-o', label='data')
    plt.xlabel('k')
    plt.ylabel('log(inertia)')
    plt.savefig('Plot-Inertia.pdf')
    plt.show()

def compute_inertia(a, X):
    W = [np.mean(pairwise_distances(X[a == c, :])) for c in np.unique(a)]
    return np.mean(W)
    
def compute_gap(clustering, data, k_max=5, n_references=5):
    if len(data.shape) == 1:
        data = data.reshape(-1, 1)
    reference = np.random.rand(*data.shape)
    reference_inertia = []
    for k in range(1, k_max+1):
        local_inertia = []
        for _ in range(n_references):
            clustering.n_clusters = k
            assignments = clustering.fit_predict(reference)
            local_inertia.append(compute_inertia(assignments, reference))
        reference_inertia.append(np.mean(local_inertia))
    
    ondata_inertia = []
    for k in range(1, k_max+1):
        clustering.n_clusters = k
        assignments = clustering.fit_predict(data)
        ondata_inertia.append(compute_inertia(assignments, data))
        
    gap = np.log(reference_inertia)-np.log(ondata_inertia)
    return gap, np.log(reference_inertia), np.log(ondata_inertia)
    
#Functions provided by the professor
def compute_ssq(data, k, kmeans):
    dist = np.min(cdist(data, kmeans.cluster_centers_, 'euclidean'), axis=1)
    tot_withinss = sum(dist**2) # Total within-cluster sum of squares
    totss = sum(pdist(data)**2) / data.shape[0] # The total sum of squares
    betweenss = totss - tot_withinss # The between-cluster sum of squares
    return betweenss/totss*100
    
#Given a data (as nxm matrix) and an array of ks, this returns the SSQ (sum of squared distances)
#SSQ is also called as SSD or SSE
def ssq_statistics(data, ks, ssq_norm=True):
    ssqs = sp.zeros((len(ks),)) # array for SSQs (length ks)

    for (i,k) in enumerate(ks): # iterate over the range of k values
        kmeans = KMeans(n_clusters=k, random_state=1234).fit(data)
        if ssq_norm:
            ssqs[i] = compute_ssq(data, k, kmeans)
        else:
            # The sum of squared error (SSQ) for k
            ssqs[i] = kmeans.inertia_
    
    return ssqs

#Method to plot the SSQ
def plot_ssq(k_values, ssqs):    

    plt.clf()#clear the plot
    plt.figure()
    plt.plot(k_values, ssqs)
    plt.xlabel("Number of cluster")
    plt.ylabel("SSQ")
    plt.show()
    
def evaluate_kmeans(data_analysis):
    
    data_analysis_df = data_analysis[['AmountSpent','Salary', 'Children', 'Catalogs', 'Age_Middle', 'Age_Old', 'Age_Young', 'Gender_Female', 'Gender_Male', 'OwnHome_Own', 'OwnHome_Rent', 'Married_Married', 'Married_Single', 'Location_Close', 'Location_Far']]
    
    data_array = data_analysis_df.to_numpy()
    #hof_entry_target = hof_entry_array[:, -1] # for last column
    #print('target--', hof_entry_target)
    # Get all columns except for last
    data_array  = data_array[:,:-1]
    #print('array', hof_entry_array)
 
    k_values = [x for x in range(1,10)]
    ssqs=ssq_statistics(data_array, k_values)
 
    print('\n\nSSQ Plot for k= 1 to 10\n','-'*40, sep='')
    plot_ssq(k_values,ssqs)
    
 
    k_max = max(k_values)
    gap, reference_inertia, ondata_inertia = compute_gap(KMeans(), data_array, k_max)
    print('\n\nGap plot for k= 10\n','-'*40, sep='')
    plot_gap(gap, k_max)  
    print('\nInertia plot for k= 10\n','-'*40, sep='')
    plot_inertia(reference_inertia, ondata_inertia, k_max)
    

def createStatisticsHeatmap(data_analysis):
    
    '''
    Creating statistics heatmap
    '''
    
    print('-'*50, sep='')
    print('Displaying statistics heatmap')
    print('-'*50, sep='')
    
    #data_analysis_df = data_analysis[['AmountSpent','Salary', 'Children', 'Catalogs', 'Age_Middle', 'Age_Old', 'Age_Young', 'Gender_Female', 'Gender_Male', 'OwnHome_Own', 'OwnHome_Rent', 'Married_Married', 'Married_Single', 'Location_Close', 'Location_Far']]
    # Professor recommended not all features should be shown in your correlation heat map. Some of these features are essentially repeats of the others (highly correlated negatively), e.g., Gender_Male and Gender_Female. 
    data_analysis_df = data_analysis[['AmountSpent','Salary', 'Children', 'Catalogs', 'Age_Middle', 'Gender_Male', 'OwnHome_Own', 'Married_Married', 'Location_Close']]
    
    plt.figure(figsize=(10, 16))
    # generating correlation heatmap 
    sns.heatmap(data_analysis_df.corr(), annot = True) 
      
    # posting correlation heatmap to output console
    plt.savefig('Marketing_Heatmap.jpg')
    plt.show() 
    
def get_kmeans_clusters(X, number_clusters):
        # Reference https://www.kaggle.com/minc33/visualizing-high-dimensional-clusters
    # Assume data_analysis contains only numerical variables
    
    #Initialize our scaler
    scaler = StandardScaler()
    
    #Scale each column in numer
    X = pd.DataFrame(scaler.fit_transform(X))
       
    #Initialize our model
    kmeans = KMeans(n_clusters = number_clusters)
                                    
    #Fit our model
    kmeans.fit(X)
    
    #Find which cluster each data-point belongs to
    clusters = kmeans.predict(X)
    
    return clusters
    
def perform_kmeans(X):
    # Reference https://www.kaggle.com/minc33/visualizing-high-dimensional-clusters
    # Assume data_analysis contains only numerical variables
    
    number_clusters = 4
    
    #Find which cluster each data-point belongs to
    clusters = get_kmeans_clusters(X, number_clusters)
    
    #Add the cluster vector to our DataFrame, X
    X['Cluster'] = clusters
    
    # Map the cluster values to match target values
    X['Cluster'] = X['Cluster'].map({0:1,1:0})
    
    
    #plotX is a DataFrame containing 5000 values sampled randomly from X
    plotX = pd.DataFrame(np.array(X))

    #Rename plotX's columns since it was briefly converted to an np.array above
    plotX.columns = X.columns
    
    #PCA with one principal component
    pca_1d = PCA(n_components=1)
    
    #PCA with two principal components
    pca_2d = PCA(n_components=2)
    
    
    #This DataFrame holds that single principal component mentioned above
    PCs_1d = pd.DataFrame(pca_1d.fit_transform(plotX.drop(["Cluster"], axis=1)))
    
    #This DataFrame contains the two principal components that will be used
    #for the 2-D visualization mentioned above
    PCs_2d = pd.DataFrame(pca_2d.fit_transform(plotX.drop(["Cluster"], axis=1)))
    

    
    PCs_1d.columns = ["PC1_1d"]

    #"PC1_2d" means: 'The first principal component of the components created for 2-D visualization, by PCA.'
    #And "PC2_2d" means: 'The second principal component of the components created for 2-D visualization, by PCA.'
    PCs_2d.columns = ["PC1_2d", "PC2_2d"]
    
    
    plotX = pd.concat([plotX,PCs_1d,PCs_2d], axis=1, join='inner')
    
    plotX["dummy"] = 0
    
    #Note that all of the DataFrames below are sub-DataFrames of 'plotX'.
    #This is because we intend to plot the values contained within each of these DataFrames.
    
    cluster0 = plotX[plotX["Cluster"] == 0]
    cluster1 = plotX[plotX["Cluster"] == 1]
    cluster1 = plotX[plotX["Cluster"] == 2]
    cluster1 = plotX[plotX["Cluster"] == 3]
    #cluster2 = plotX[plotX["Cluster"] == 2]
    
    #Instructions for building the 1-D plot

    #trace1 is for 'Cluster 0'
    trace1 = go.Scatter(
                        x = cluster0["PC1_1d"],
                        y = cluster0["dummy"],
                        mode = "markers",
                        name = "Cluster 0",
                        marker = dict(color = 'rgba(255, 128, 255, 0.8)'),
                        text = None)
    


    
    #trace2 is for 'Cluster 1'
    trace2 = go.Scatter(
                        x = cluster1["PC1_1d"],
                        y = cluster1["dummy"],
                        mode = "markers",
                        name = "Cluster 1",
                        marker = dict(color = 'rgba(255, 128, 2, 0.8)'),
                        text = None)
    
    #trace3 is for 'Cluster 2'
    trace3 = go.Scatter(
                        x = cluster1["PC1_1d"],
                        y = cluster1["dummy"],
                        mode = "markers",
                        name = "Cluster 2",
                        marker = dict(color = 'rgba(0, 255, 200, 0.8)'),
                        text = None)
    
    #trace4 is for 'Cluster 3'
    trace4 = go.Scatter(
                        x = cluster1["PC1_1d"],
                        y = cluster1["dummy"],
                        mode = "markers",
                        name = "Cluster 3",
                        marker = dict(color = 'red'),
                        text = None)


    data = [trace1, trace2, trace3, trace4]
    
    title = "Visualizing Clusters in One Dimension Using PCA"
    
    layout = dict(title = title,
                  xaxis= dict(title= 'PC1',ticklen= 5,zeroline= False),
                  yaxis= dict(title= '',ticklen= 5,zeroline= False)
                 )
    
    fig = dict(data = data, layout = layout)
    
    plot(fig, filename='1D-PCA.html')
    
    
    #Instructions for building the 2-D plot

    #trace1 is for 'Cluster 0'
    trace1 = go.Scatter(
                        x = cluster0["PC1_2d"],
                        y = cluster0["PC2_2d"],
                        mode = "markers",
                        name = "Cluster 0",
                        marker = dict(color = 'rgba(255, 128, 255, 0.8)'),
                        text = None)
    
    #trace2 is for 'Cluster 1'
    trace2 = go.Scatter(
                        x = cluster1["PC1_2d"],
                        y = cluster1["PC2_2d"],
                        mode = "markers",
                        name = "Cluster 1",
                        marker = dict(color = 'rgba(255, 128, 2, 0.8)'),
                        text = None)
    
    #trace3 is for 'Cluster 2'
    trace3 = go.Scatter(
                        x = cluster1["PC1_1d"],
                        y = cluster1["dummy"],
                        mode = "markers",
                        name = "Cluster 2",
                        marker = dict(color = 'rgba(0, 255, 200, 0.8)'),
                        text = None)
    
    #trace4 is for 'Cluster 3'
    trace4 = go.Scatter(
                        x = cluster1["PC1_1d"],
                        y = cluster1["dummy"],
                        mode = "markers",
                        name = "Cluster 3",
                        marker = dict(color = 'red'),
                        text = None)
    
    data = [trace1, trace2, trace3, trace4]
    
    title = "Visualizing Clusters in Two Dimensions Using PCA"
    
    layout = dict(title = title,
                  xaxis= dict(title= 'PC1',ticklen= 5,zeroline= False),
                  yaxis= dict(title= 'PC2',ticklen= 5,zeroline= False)
                 )
    
    fig = dict(data = data, layout = layout)
    
    plot(fig, filename='2D-PCA.html')
    
    return clusters
    
    