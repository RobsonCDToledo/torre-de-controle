# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "f6b1f2f6-b88e-4122-898d-b8fc04b30459",
# META       "default_lakehouse_name": "lh_silver",
# META       "default_lakehouse_workspace_id": "528a4166-a694-4105-90bd-d6509fcc0536",
# META       "known_lakehouses": [
# META         {
# META           "id": "f6b1f2f6-b88e-4122-898d-b8fc04b30459"
# META         }
# META       ]
# META     }
# META   }
# META }

# CELL ********************

# Welcome to your new notebook
# Type here in the cell editor to add code!

spark.sql("SHOW TABLES").show()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

spark.sql("SHOW TABLES IN lh_silver")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
