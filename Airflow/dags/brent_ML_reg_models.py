import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
from sklearn.metrics import r2_score
from mysql.connector import connect,Error
from getpass import getpass
from sqlalchemy import create_engine
import pymysql

def create_database():
    try:
        with connect(
                host="localhost",
                user="airflowmysqluser",
                password="airflow"
        ) as conn:
            drop_db_query = 'drop schema if exists brent_pricing_db;'
            create_db_query = "create schema brent_pricing_db;"
            with conn.cursor() as cur:
                cur.execute(drop_db_query)
                cur.execute(create_db_query)
    except Error as e:
        print(e)



def import_dataset():
    """
    This function reads the data from csv file and organizes/cleans/wrangles it into required dataset
    """
    create_database()

    dataset=pd.read_csv('/Users/ballakeerthi/dev/Airflow/dags/Europe_Brent_Spot_Price_FOB.csv', sep='delimiter', header=None, parse_dates=True)
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

# import_dataset()

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

# create_dummy_vars()

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
    y=dataset.iloc[:,0].values
    y=y.reshape(len(y),1)
    x=pd.DataFrame(x,columns=column_names[1:])
    y=pd.DataFrame(y)
    y.columns=[column_names[0]]

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

# IV_DV_split()

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
    except Error as e:
        print(e)
    else:
        print("Tables x,y for training & testing sets are created successfully")
    finally:
        dbConnection.close()
    # (END) ###############################################

# split_train_test_sets()

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
    except Error as e:
        print(e)
    else:
        print("Results table successfully updated")
    finally:
        dbConnection.close()
    # (END) ###############################################

    # return "multiple linear regression", r_sq_score

# multiple_lin_reg()

def random_forest_reg():
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

    from sklearn.ensemble import RandomForestRegressor
    regressor = RandomForestRegressor(n_estimators = 10, random_state = 0)
    regressor.fit(x_train, y_train)
    y_pred = regressor.predict(x_test)
    r_sq_score = r2_score(y_test, y_pred)

    #########################################################
    # store r2_score to results_table in brent db
    # (START) ###############################################
    # sqlEngine = create_engine('mysql+pymysql://airflowmysqluser:airflow@localhost/brent_pricing_db', pool_recycle=3600)
    # dbConnection = sqlEngine.connect()

    tableName = "results_table"

    try:
        dbConnection.execute("insert into results_table values ('r_f_r', %s)", r_sq_score)
        # dbConnection.commit()
    except Error as e:
        print(e)
    else:
        print("Results table successfully updated")
    finally:
        dbConnection.close()
    # (END) ###############################################

    # return "random forest regression", r_sq_score

# random_forest_reg()

def decision_tree_reg():
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

    from sklearn.tree import DecisionTreeRegressor
    regressor = DecisionTreeRegressor(random_state=1)
    regressor.fit(x_train,y_train)
    y_pred = regressor.predict(x_test)
    r_sq_score = r2_score(y_test, y_pred)
    #########################################################
    # store r2_score to results_table in brent db
    # (START) ###############################################
    # sqlEngine = create_engine('mysql+pymysql://airflowmysqluser:airflow@localhost/brent_pricing_db', pool_recycle=3600)
    # dbConnection = sqlEngine.connect()

    tableName = "results_table"

    try:
        dbConnection.execute("insert into results_table values ('d_t_r', %s)", r_sq_score)
        # dbConnection.commit()
    except Error as e:
        print(e)
    else:
        print("Results table successfully updated")
    finally:
        dbConnection.close()
    # (END) ###############################################

    # return "decision tree regression", r_sq_score

# decision_tree_reg()

def choose_best_model():
    #########################################################
    # read from a table to a dataset in brent db
    # (START) ###############################################
    sqlEngine = create_engine('mysql+pymysql://airflowmysqluser:airflow@localhost/brent_pricing_db', pool_recycle=3600)
    dbConnection = sqlEngine.connect()
    tableName = "results_table"
    try:
        results = pd.read_sql_table(tableName,dbConnection)
        # results = results.drop(['index'],axis=1)

    except Error as e:
        print(e)
    else:
        print("Results Dataset is created successfully")
    finally:
        dbConnection.close()
    # (END) ###############################################

    best_model = results.iloc[results.r_sq_score.argmax(), 0]
    r_sq_score = results.iloc[results.r_sq_score.argmax(), 1]
    if best_model == 'm_l_r':
        print("The best model is Multiple Linear Regression with R square score of", r_sq_score)
    elif best_model == 'r_f_r':
        print("The best model is Random Forest Regression with R square score of", r_sq_score)
    else:
        print("The best model is Decision Tree Regression with R square score of", r_sq_score)

# choose_best_model()


