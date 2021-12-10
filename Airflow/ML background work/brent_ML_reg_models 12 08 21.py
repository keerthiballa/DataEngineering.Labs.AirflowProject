import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
from sklearn.metrics import r2_score
from mysql.connector import connect,Error
from getpass import getpass
from sqlalchemy import create_engine
import pymysql

# def create_table(tableName,dataFrame): ---> to use the function content as code snippet in below functions and not to call it as such
#     dbConnection = sqlEngine.connect()
#     try:
#         frame = dataFrame.to_sql(tableName, dbConnection, if_exists='fail')
#     except Error as e:
#         print(e)
#     else:
#         print("Table %s created successfully," %tableName)
#     finally:
#         dbConnection.close()

def create_database():
    try:
        with connect(
                host="localhost",
                user="airflowmysqluser",
                password="airflow"
        ) as conn:
            create_db_query = "create schema brent_pricing_db;"
            with conn.cursor() as cur:
                cur.execute(create_db_query)
    except Error as e:
        print(e)

create_database()

def import_dataset():
    """
    This function reads the data from csv file and organizes/cleans/wrangles it into required dataset
    """
    dataset=pd.read_csv('/dags/Europe_Brent_Spot_Price_FOB.csv', sep='delimiter', header=None, parse_dates=True)
    dataset[['Date','Price']]=dataset[0].str.split(',', expand=True)

    dataset=dataset.drop([0,1,2,3,4,5])
    dataset=dataset.drop([0],axis=1)

    dataset['Date'] = pd.to_datetime(dataset['Date'])
    dataset['Date'] = dataset['Date'].dt.strftime('%d.%m.%Y')
    dataset['year'] = pd.DatetimeIndex(dataset['Date']).year
    dataset['month'] = pd.DatetimeIndex(dataset['Date']).month
    dataset['day'] = pd.DatetimeIndex(dataset['Date']).day
    dataset['dayofyear'] = pd.DatetimeIndex(dataset['Date']).dayofyear
    dataset['weekofyear'] = pd.DatetimeIndex(dataset['Date']).weekofyear
    dataset['weekday'] = pd.DatetimeIndex(dataset['Date']).weekday
    dataset['quarter'] = pd.DatetimeIndex(dataset['Date']).quarter
    dataset['is_month_start'] = pd.DatetimeIndex(dataset['Date']).is_month_start
    dataset['is_month_end'] = pd.DatetimeIndex(dataset['Date']).is_month_end

    dataset=dataset.drop(['Date'],axis=1)
    dataset['Price'] = dataset['Price'].astype('float')
    #########################################################
    # store dataset to a table in brent db
    # (START) ###############################################
    sqlEngine = create_engine('mysql+pymysql://airflowmysqluser:airflow@localhost/brent_pricing_db', pool_recycle=3600)
    dbConnection = sqlEngine.connect()
    tableName="dataset_table"
    try:
        frame = dataset.to_sql(tableName, dbConnection, if_exists='replace')
    except Error as e:
        print(e)
    else:
        print("Table %s created successfully," %tableName)
    finally:
        dbConnection.close()
    # (END) ###############################################
    # return dataset
    # print(dataset.head())
import_dataset()

def create_dummy_vars():
    """
    This function creates dummy variables
    """
    #########################################################
    # read from a table to a dataset in brent db
    # (START) ###############################################
    sqlEngine = create_engine('mysql+pymysql://airflowmysqluser:airflow@localhost/brent_pricing_db', pool_recycle=3600)
    dbConnection = sqlEngine.connect()
    tableName = "dataset_table"
    try:
        dataset = pd.read_sql_table(tableName,dbConnection)
        dataset=dataset.drop(['index'],axis=1)
        dbConnection.execute('drop table %s' %tableName)
    except Error as e:
        print(e)
    else:
        print("Dataset is created successfully")
    # finally:
    #     dbConnection.close()
    # (END) ###############################################

    dataset = pd.get_dummies(dataset, columns=['year'], drop_first=True, prefix='year')
    dataset = pd.get_dummies(dataset, columns=['month'], drop_first=True, prefix='month')
    dataset = pd.get_dummies(dataset, columns=['weekday'], drop_first=True, prefix='wday')
    dataset = pd.get_dummies(dataset, columns=['quarter'], drop_first=True, prefix='qrtr')
    dataset = pd.get_dummies(dataset, columns=['is_month_start'], drop_first=True, prefix='m_start')
    dataset = pd.get_dummies(dataset, columns=['is_month_end'], drop_first=True, prefix='m_end')

    #########################################################
    # store dataset to a table in brent db
    # (START) ###############################################
    # sqlEngine = create_engine('mysql+pymysql://airflowmysqluser:airflow@localhost/brent_pricing_db', pool_recycle=3600)
    # dbConnection = sqlEngine.connect()
    tableName="dataset_table"
    try:
        dataset.to_sql(tableName, dbConnection, if_exists='replace')
    except Error as e:
        print(e)
    else:
        print("Table %s created successfully," %tableName)
    finally:
        dbConnection.close()
    # (END) ###############################################

    # return dataset

create_dummy_vars()

def IV_DV_split():
    """
    This function assigns independent variables to x and dependent variable to y
    """
    #########################################################
    # read from a table to a dataset in brent db
    # (START) ###############################################
    sqlEngine = create_engine('mysql+pymysql://airflowmysqluser:airflow@localhost/brent_pricing_db', pool_recycle=3600)
    dbConnection = sqlEngine.connect()
    tableName = "dataset_table"
    try:
        dataset = pd.read_sql_table(tableName, dbConnection)
        dataset = dataset.drop(['index'], axis=1)
        column_names=list(dataset.columns)
        print(column_names)
        print(type(column_names))
        print(len(column_names))
        print(column_names[0])
        dbConnection.execute('drop table %s' % tableName)
        # print(dataset.head())
    except Error as e:
        print(e)
    else:
        print("Dataset is created successfully")
    # finally:
    #     dbConnection.close()
    # (END) ###############################################

    x=dataset.iloc[:,1:].values
    print("2: Shape of x dataset is ",x.shape)
    y=dataset.iloc[:,0].values
    # print("3: Shape of y dataset is ", y.shape)
    y=y.reshape(len(y),1)
    # print("3.5: Shape of y dataset is ", y.shape)

    x=pd.DataFrame(x,columns=column_names[1:])
    # print("4 type of x is",type(x))
    # print("4",x.head())
    y=pd.DataFrame(y)
    print("Shape of y dataset is ",y.shape)
    y.columns=[column_names[0]]
    print("5",y.head())
    # return x,y

    #########################################################
    # store datasets to tables in brent db
    # (START) ###############################################
    # sqlEngine = create_engine('mysql+pymysql://airflowmysqluser:airflow@localhost/brent_pricing_db', pool_recycle=3600)
    # dbConnection = sqlEngine.connect()
    tableNamex = "dataset_x_table"
    tableNamey = "dataset_y_table"
    try:
        x.to_sql(tableNamex, dbConnection, if_exists='replace')
        y.to_sql(tableNamey, dbConnection, if_exists='replace')
    except Error as e:
        print(e)
    else:
        print("Table %s created successfully," %tableNamex)
        print("Table %s created successfully," %tableNamey)
    finally:
        dbConnection.close()
    # (END) ###############################################

IV_DV_split()

def split_train_test_sets():
    """
    This function splits the data into training set and testing set. Selection is given to split the data on random basis
    """
    #########################################################
    # read from x&y tables to x&y datasets in brent db
    # (START) ###############################################
    sqlEngine = create_engine('mysql+pymysql://airflowmysqluser:airflow@localhost/brent_pricing_db', pool_recycle=3600)
    dbConnection = sqlEngine.connect()
    tableNamex = "dataset_x_table"
    tableNamey = "dataset_y_table"
    try:
        x = pd.read_sql_table(tableNamex, dbConnection)
        x = x.drop(['index'], axis=1)
        y = pd.read_sql_table(tableNamey, dbConnection)
        y = y.drop(['index'], axis=1)
        dbConnection.execute('drop table %s' %tableNamex)
        dbConnection.execute('drop table %s' %tableNamey)
        # print(x.head())
    except Error as e:
        print(e)
    else:
        print("Dataset is created successfully")
    # finally:
    #     dbConnection.close()
    # (END) ###############################################

    from sklearn.model_selection import train_test_split
    x_train, x_test, y_train, y_test = train_test_split(x,y,test_size=0.2,random_state=1)
    # return x_train,y_train,x_test,y_test

    #########################################################
    # store datasets to tables in brent db
    # (START) ###############################################
    # sqlEngine = create_engine('mysql+pymysql://airflowmysqluser:airflow@localhost/brent_pricing_db', pool_recycle=3600)
    # dbConnection = sqlEngine.connect()
    tableNamexTrain = "dataset_x_train_table"
    tableNameyTrain = "dataset_y_train_table"
    tableNamexTest = "dataset_x_test_table"
    tableNameyTest = "dataset_y_test_table"

    try:
        x_train.to_sql(tableNamexTrain, dbConnection, if_exists='replace')
        y_train.to_sql(tableNameyTrain, dbConnection, if_exists='replace')
        x_test.to_sql(tableNamexTest, dbConnection, if_exists='replace')
        y_test.to_sql(tableNameyTest, dbConnection, if_exists='replace')
        #
        # x_train.to_sql(tableNamexTrain_rfr, dbConnection, if_exists='replace')
        # y_train.to_sql(tableNameyTrain_rfr, dbConnection, if_exists='replace')
        # x_test.to_sql(tableNamexTest_rfr, dbConnection, if_exists='replace')
        # y_test.to_sql(tableNameyTest_rfr, dbConnection, if_exists='replace')
        # x_train.to_sql(tableNamexTrain_dtr, dbConnection, if_exists='replace')
        # y_train.to_sql(tableNameyTrain_dtr, dbConnection, if_exists='replace')
        # x_test.to_sql(tableNamexTest_dtr, dbConnection, if_exists='replace')
        # y_test.to_sql(tableNameyTest_dtr, dbConnection, if_exists='replace')
        # x_train.to_sql(tableNamexTrain_svr, dbConnection, if_exists='replace')
        # y_train.to_sql(tableNameyTrain_svr, dbConnection, if_exists='replace')
        # x_test.to_sql(tableNamexTest_svr, dbConnection, if_exists='replace')
        # y_test.to_sql(tableNameyTest_svr, dbConnection, if_exists='replace')
    except Error as e:
        print(e)
    else:
        print("Tables x,y for training & testing sets are created successfully")
    finally:
        dbConnection.close()
    # (END) ###############################################

split_train_test_sets()

def feature_scaling():
    """
    This function is only for Support Vector Regression to normalize the data
    """
    #########################################################
    # read from x&y tables to x&y datasets in brent db
    # (START) ###############################################
    sqlEngine = create_engine('mysql+pymysql://airflowmysqluser:airflow@localhost/brent_pricing_db', pool_recycle=3600)
    dbConnection = sqlEngine.connect()
    tableNamexTrain = "dataset_x_train_table"
    tableNameyTrain = "dataset_y_train_table"
    tableNamexTest = "dataset_x_test_table"
    tableNameyTest = "dataset_y_test_table"
    try:
        x_train = pd.read_sql_table(tableNamexTrain, dbConnection)
        x_train = x_train.drop(['index'], axis=1)
        x_train_column_names=list(x_train.columns)

        y_train = pd.read_sql_table(tableNameyTrain, dbConnection)
        y_train = y_train.drop(['index'], axis=1)
        y_train_column_names=list(y_train.columns)

        print(x_train_column_names)
        print(type(x_train_column_names))
        print(len(x_train_column_names))
        print(x_train_column_names[0])
        print(y_train_column_names)
        print(type(y_train_column_names))
        print(len(y_train_column_names))
        print(y_train_column_names[0])
    except Error as e:
        print(e)
    else:
        print("Training and testing Datasets for x and y are created successfully and the original tables in SQL are retained")
    # finally:
    #     dbConnection.close()
    # (END) ###############################################

    from sklearn.preprocessing import StandardScaler
    sc_x = StandardScaler()
    sc_y = StandardScaler()
    x_train = sc_x.fit_transform(x_train)
    y_train = sc_y.fit_transform(y_train)
    # return x_train,y_train,sc_x,sc_y
    x_train = pd.DataFrame(x_train, columns=x_train_column_names[:])
    # print("4 type of x is",type(x))
    # print("4",x.head())
    y_train = pd.DataFrame(y_train)
    y_train.columns = [y_train_column_names[0]]
    #########################################################
    # store datasets to tables in brent db
    # (START) ###############################################
    # sqlEngine = create_engine('mysql+pymysql://airflowmysqluser:airflow@localhost/brent_pricing_db', pool_recycle=3600)
    # dbConnection = sqlEngine.connect()

    tableName_sc_x_train = "dataset_sc_x_train_table"
    tableName_sc_y_train = "dataset_sc_y_train_table"

    try:
        x_train.to_sql(tableName_sc_x_train, dbConnection, if_exists='replace')
        y_train.to_sql(tableName_sc_y_train, dbConnection, if_exists='replace')

    except Error as e:
        print(e)
    else:
        print("Tables sc_x_train, sc_y_train are created successfully")
    finally:
        dbConnection.close()
    # (END) ###############################################

feature_scaling()

def multiple_lin_reg():
    """
    This function is to create a regressor variable that is an instance of regression model imported from sklearn module.
    This function also finds out the predicted value of dependent variable y based on our model and calculate the R square score comparing y pred with y test
    """
    #########################################################
    # read from x train, x test, y train & y test tables to x train, x test, y train & y test datasets in brent db
    # (START) ###############################################
    sqlEngine = create_engine('mysql+pymysql://airflowmysqluser:airflow@localhost/brent_pricing_db', pool_recycle=3600)
    dbConnection = sqlEngine.connect()
    tableNamexTrain = "dataset_x_train_table"
    tableNameyTrain = "dataset_y_train_table"
    tableNamexTest = "dataset_x_test_table"
    tableNameyTest = "dataset_y_test_table"
    try:
        x_train = pd.read_sql_table(tableNamexTrain, dbConnection)
        x_train = x_train.drop(['index'], axis=1)
        x_train_column_names=list(x_train.columns)

        y_train = pd.read_sql_table(tableNameyTrain, dbConnection)
        y_train = y_train.drop(['index'], axis=1)
        y_train_column_names=list(y_train.columns)

        x_test = pd.read_sql_table(tableNamexTest, dbConnection)
        x_test = x_test.drop(['index'], axis=1)
        x_test_column_names = list(x_test.columns)

        y_test = pd.read_sql_table(tableNameyTest, dbConnection)
        y_test = y_test.drop(['index'], axis=1)
        y_test_column_names = list(y_test.columns)


    except Error as e:
        print(e)
    else:
        print("Training and testing Datasets for x and y are created successfully and the original tables in SQL are retained")
    # finally:
    #     dbConnection.close()
    # (END) ###############################################

    from sklearn.linear_model import LinearRegression
    regressor=LinearRegression()
    regressor.fit(x_train,y_train)
    # return regressor
    y_pred = regressor.predict(x_test)
    r_sq_score = r2_score(y_test, y_pred)

    #########################################################
    # store r2_score to results_table in brent db
    # (START) ###############################################
    # sqlEngine = create_engine('mysql+pymysql://airflowmysqluser:airflow@localhost/brent_pricing_db', pool_recycle=3600)
    # dbConnection = sqlEngine.connect()

    tableName = "results_table"

    try:
        dbConnection.execute("create table results_table (regression varchar(255), r_sq_score float)")
        dbConnection.execute("insert into results_table values ('m_l_r', %s)", r_sq_score)
        # dbConnection.commit()
    except Error as e:
        print(e)
    else:
        print("Results table successfully updated")
    finally:
        dbConnection.close()
    # (END) ###############################################

multiple_lin_reg()

def support_vec_reg():
    """
    This function is to create a regressor variable that is an instance of regression model imported from sklearn module.
    This function also finds out the predicted value of dependent variable y based on our model and calculate the R square score comparing y pred with y test
    """
    #########################################################
    # read from x train, x test, y train & y test tables to x train, x test, y train & y test datasets in brent db
    # (START) ###############################################
    sqlEngine = create_engine('mysql+pymysql://airflowmysqluser:airflow@localhost/brent_pricing_db', pool_recycle=3600)
    dbConnection = sqlEngine.connect()
    tableName_sc_xTrain = "dataset_sc_x_train_table"
    tableName_sc_yTrain = "dataset_sc_y_train_table"
    tableNamexTest = "dataset_x_test_table"
    tableNameyTest = "dataset_y_test_table"
    try:
        x_train = pd.read_sql_table(tableName_sc_xTrain, dbConnection)
        x_train = x_train.drop(['index'], axis=1)
        x_train_column_names=list(x_train.columns)

        y_train = pd.read_sql_table(tableName_sc_yTrain, dbConnection)
        y_train = y_train.drop(['index'], axis=1)
        y_train_column_names=list(y_train.columns)

        x_test = pd.read_sql_table(tableNamexTest, dbConnection)
        x_test = x_test.drop(['index'], axis=1)
        x_test_column_names = list(x_test.columns)

        y_test = pd.read_sql_table(tableNameyTest, dbConnection)
        y_test = y_test.drop(['index'], axis=1)
        y_test_column_names = list(y_test.columns)


    except Error as e:
        print(e)
    else:
        print("Training and testing Datasets for x and y are created successfully and the original tables in SQL are retained")
    # finally:
    #     dbConnection.close()
    # (END) ###############################################
    from sklearn.svm import SVR
    regressor=SVR(kernel='rbf')
    regressor.fit(x_train,y_train)
    # return regressor

    from sklearn.preprocessing import StandardScaler
    sc_x = StandardScaler()
    sc_y = StandardScaler()
    x_train=sc_x.fit_transform(x_train)
    y_train=sc_y.fit_transform(y_train)

    # sc_x_test=StandardScaler()
    # x_test=sc_x_test.fit_transform(x_test)
    # y_pred = sc_y.inverse_transform(regressor.predict(x_test))

    r_sq_score=predict_test_set_r2_score_s_v_r()


    # r2_score(y_test,y_pred)
    # return "Support Vector Regression", r2_score(y_test,y_pred)

    #########################################################
    # store r2_score to results_table in brent db
    # (START) ###############################################
    # sqlEngine = create_engine('mysql+pymysql://airflowmysqluser:airflow@localhost/brent_pricing_db', pool_recycle=3600)
    # dbConnection = sqlEngine.connect()

    tableName = "results_table"

    try:
        # dbConnection.execute("create table results_table (regression varchar(255), r_sq_score float)")
        dbConnection.execute("insert into results_table values ('s_v_r', %s)", r_sq_score)
        # dbConnection.commit()
    except Error as e:
        print(e)
    else:
        print("Results table successfully updated")
    finally:
        dbConnection.close()
    # (END) ###############################################

def predict_test_set_r2_score_s_v_r():
    """
    This function is to find the predicted value of dependent variable y based on our model and calculate the R square score comparing y pred with y test
    """
    sqlEngine = create_engine('mysql+pymysql://airflowmysqluser:airflow@localhost/brent_pricing_db', pool_recycle=3600)
    dbConnection = sqlEngine.connect()
    tableName_sc_xTrain = "dataset_sc_x_train_table"
    tableName_sc_yTrain = "dataset_sc_y_train_table"
    tableNamexTest = "dataset_x_test_table"
    tableNameyTest = "dataset_y_test_table"
    try:
        x_train = pd.read_sql_table(tableName_sc_xTrain, dbConnection)
        x_train = x_train.drop(['index'], axis=1)
        x_train_column_names = list(x_train.columns)

        y_train = pd.read_sql_table(tableName_sc_yTrain, dbConnection)
        y_train = y_train.drop(['index'], axis=1)
        y_train_column_names = list(y_train.columns)

        x_test = pd.read_sql_table(tableNamexTest, dbConnection)
        x_test = x_test.drop(['index'], axis=1)
        x_test_column_names = list(x_test.columns)

        y_test = pd.read_sql_table(tableNameyTest, dbConnection)
        y_test = y_test.drop(['index'], axis=1)
        y_test_column_names = list(y_test.columns)

    except Error as e:
        print(e)
    else:
        print(
            "Training and testing Datasets for x and y are created successfully and the original tables in SQL are retained")
    # finally:
    #     dbConnection.close()
    # (END) ###############################################

    from sklearn.svm import SVR
    regressor = SVR(kernel='rbf')
    regressor.fit(x_train, y_train)

    from sklearn.preprocessing import StandardScaler
    sc_x = StandardScaler()
    sc_y = StandardScaler()
    # sc_x_test=StandardScaler()
    x_train = sc_x.fit_transform(x_train)
    # x_train=x_train.reshape(1,-1)
    y_train = sc_y.fit_transform(y_train)
    # y_train = y_train.reshape(1, -1)
    print(type(sc_x.transform(x_test)))
    print(sc_x.transform(x_test).shape)
    # y_pred=regressor.predict(x_test)

    y_pred = sc_y.inverse_transform(regressor.predict(sc_x.transform(x_test)).reshape(len(y_test),1))

    print(y_pred.shape)
    print(y_test.shape)
    return r2_score(y_test,y_pred)

support_vec_reg()

def random_forest_reg(x_train,y_train):
    """
    This function is to create a regressor variable that is an instance of regression model imported from sklearn module
    """
    from sklearn.ensemble import RandomForestRegressor
    regressor = RandomForestRegressor(n_estimators = 10, random_state = 0)
    regressor.fit(x_train, y_train)
    # return regressor

def decision_tree_reg(x_train,y_train):
    """
    This function is to create a regressor variable that is an instance of regression model imported from sklearn module
    """
    from sklearn.tree import DecisionTreeRegressor
    regressor = DecisionTreeRegressor(random_state=1)
    regressor.fit(x_train,y_train)
    return regressor

def predict_test_set_r2_score_m_l_r(regressor,x_test,y_test):
    """
    This function is to find the predicted value of dependent variable y based on our model and calculate the R square score comparing y pred with y test
    """
    y_pred = regressor.predict(x_test)
    return "Multiple Linear Regression", r2_score(y_test,y_pred)

def predict_test_set_r2_score_d_t_r(regressor,x_test,y_test):
    """
    This function is to find the predicted value of dependent variable y based on our model and calculate the R square score comparing y pred with y test
    """
    y_pred = regressor.predict(x_test)
    return "Decision Tree Regression", r2_score(y_test,y_pred)

def predict_test_set_r2_score_r_f_r(regressor,x_test,y_test):
    """
    This function is to find the predicted value of dependent variable y based on our model and calculate the R square score comparing y pred with y test
    """
    y_pred = regressor.predict(x_test)
    return "Random Forest Regression", r2_score(y_test,y_pred)

