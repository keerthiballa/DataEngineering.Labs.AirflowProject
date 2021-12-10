from airflow import DAG #to instantiate a DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.bash import BashOperator
from brent_ML_reg_models import *
from datetime import datetime, timedelta
from airflow.providers.mysql.operators.mysql import MySqlOperator

# print(sys.path)

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email': ['keerthiballa@gmail.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    # 'retries': 2,
    'retry_delay': timedelta(seconds=10)
    # 'queue': 'bash_queue',
    # 'pool': 'backfill',
    # 'priority_weight': 10,
    # 'end_date': datetime(2016, 1, 1),
    # 'wait_for_downstream': False,
    # 'dag': dag,
    # 'sla': timedelta(hours=2),
    # 'execution_timeout': timedelta(seconds=300),
    # 'on_failure_callback': some_function,
    # 'on_success_callback': some_other_function,
    # 'on_retry_callback': another_function,
    # 'sla_miss_callback': yet_another_function,
    # 'trigger_rule': 'all_success'
}


def _choose_best_model(ti):
    model_m_l_r = ti.xcom_pull(task_ids=['t5'])
    model_r_f_r = ti.xcom_pull(task_ids=['t6'])
    model_d_t_r = ti.xcom_pull(task_ids=['t7'])

    # best_model_score = max(model_m_l_r[1],model_r_f_r[1],model_d_t_r[1])
    models=[model_m_l_r,model_r_f_r,model_d_t_r]

    highest_val=0
    best_model=""
    for i in models:
        if i[1]>highest_val:
            highest_val=i[1]
            best_model=i[0]

    print("The best model is ",best_model,"with r square score of ",highest_val)


with DAG(dag_id="brent_pricing_dag", default_args=default_args, start_date=datetime(2021,12,4), schedule_interval="@daily", catchup=False) as dag:

    t1 = PythonOperator(
        task_id="Import_the_dataset_and_clean_the_data",
        python_callable=import_dataset,
        provide_context=True
    )

    t2 = PythonOperator(
        task_id="Create_dummy_variables",
        python_callable=create_dummy_vars
    )

    t3 = PythonOperator(
        task_id="x_y_values",
        python_callable=IV_DV_split
    )

    t4 = PythonOperator(
        task_id="Split_the_dataset_into_training_and_test_sets",
        python_callable=split_train_test_sets
    )

    t5= PythonOperator(
        task_id="Train_the_Regression_Model_MLR_on_the_training_set",
        python_callable=multiple_lin_reg
    )

    t6 = PythonOperator(
        task_id="Train_the_Regression_Model_RFR_on_the_training_set",
        python_callable=random_forest_reg
    )

    t7 = PythonOperator(
        task_id="Train_the_Regression_Model_DTR_on_the_training_set",
        python_callable=decision_tree_reg
    )

    mysql_task = MySqlOperator(
        task_id='drop_database_mysql_external_file',
        sql='drop schema if exists brent_pricing_db' #,
        # dag=dag
    )


choose_best_model = BranchPythonOperator(

    task_id="choose_best_model",
    python_callable=_choose_best_model
)


mysql_task >> t1
t1 >> t2 >> t3 >> t4 >> t5
t1 >> t2 >> t3 >> t4 >> t6
t1 >> t2 >> t3 >> t4 >> t7

[t5,t6,t7] >> choose_best_model
