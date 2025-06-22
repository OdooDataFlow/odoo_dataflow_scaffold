# odoo_dataflow_scaffold

**odoo_dataflow_scaffold accelarates** the development of import/export projects using [odoo-data-flow](https://github.com/OdooDataFlow/odoo-data-flow) tools It provides two main functions:

* **Creates** the folders structure and a basic set of files that organize the project.
* **Generates** skeleton code that applies transformations to a client file before importing it into Odoo.


The skeleton code documents the fields thoroughly, eliminating the need to look up their definitions with an external tool. A field analysis automatically suggests to exclude some of them when they shoud not be imported.
Each new skeleton code is fully integrated in the other project files.

## Table of Contents

- [odoo_datalow_scaffold](#odoodataflowscaffold)
  - [Table Of Content](#table-of-content)
- [1. Installation](#1-installation)
- [2. How To Use It](#2-how-to-use-it)
  - [2.1. Create the project structure](#21-create-the-project-structure)
  - [2.2. Generate a model skeleton code](#22-generate-a-model-skeleton-code)
  - [2.3. Setup the project and review the generated code](#23-setup-the-project-and-review-the-generated-code)
  - [2.4. Repeat the steps 2.2 and 2.3](#24-repeat-the-steps-22-and-23)
  - [2.5. Launch the transformation script](#25-launch-the-transformation-script)
  - [2.6. Launch the load script](#26-launch-the-load-script)
- [3. Folders Structure and Project Files](#3-folders-structure-and-project-files)
  - [3.1. Created Folders and Files](#31-created-folders-and-files)
  - [3.2. Scaffolding Options](#32-scaffolding-options)
- [4. Model Skeleton Codes](#4-model-skeleton-codes)
  - [4.1. Skeleton Types](#41-skeleton-types)
  - [4.2. Fields Selection](#42-fields-selection)
  - [4.3. Fields Information](#43-fields-information)
  - [4.4. Other Skeleton Options](#44-other-skeleton-options)
- [5. Command Line Tricks](#5-command-line-tricks)
- [6. How-To](#6-how-to)
- [7. Requirements](#7-requirements)
  - [7.1. On your local computer](#71-on-your-local-computer)
  - [7.2. On the target database](#72-on-the-target-database)
- [8. Known Issues](#8-known-issues)

# 1. Installation

<!-- * From GitHub -->
To install `odoo_dataflow_scaffold` from GitHub, use the following command:

```bash
git clone git@github.com:OdooDataFlow/odoo_dataflow_scaffold.git
```

<!-- * From PyPi  -->

```bash
[sudo] pip install odoo_dataflow_scaffold
```


# 2. How To Use It

## 2.1. Create the project structure
      
To create the project structure, run the following command:

```bash
odoo_dataflow_scaffold.py -s -p project_dir [-d my_db] [-t my_db.odoo.com]
```

This command creates the necessary directories (e.g., `conf/`, `data/`) and files (e.g., `conf/connection.conf`, `prefix.py`) within the `project_dir` directory. For a detailed description of the structure, see [Folders Structure and Project Files](#31-created-folders-and-files).

The main options are:

* `-s | --scaffold`: Creates the directory structure and the basic project files.
* `-p | --path`: Sets the project path. The default is the current directory.
* `-d | --db`: Sets the target database. If omitted, the database name defaults to the first part of the hostname.
* `-t | --host`: Sets the hostname of the database. The default is "localhost".
* `-u | --userid`: Sets the user ID used by RPC calls. The default is "2".

For more information on project scaffolding, see [Folders Structure and Project Files](#3-folders-structure-and-project-files).

## 2.2. Generate a model skeleton code
   
From your project folder, verify the connection parameters in `conf/connection.conf` and generate the skeleton code for a model:

```
odoo_dataflow_scaffold.py -m my.model -a [--map-selection] [--with-xmlid]
```

This will create the python script _my_model.py_ containing a basic skeleton code suited to import data into the model _my.model_ thanks to the mappers of `odoo-data-flow`. This will also update the other project files to take this new script into account.

The main options are:

* `-m | --model`: sets the model to generate (ex: res.partner).
* `-a | --append`: adds the created references to the project files. Use this option one time per model. Don't use it if you regenerate an existing skeleton code.
* `--map-selection`: generates mapping dictionaries for selection fields. Use this option if your client file uses selection values different than the technical values of the selection fields. Use it one time per model. Don't use it if you regenerate an existing skeleton code.
* `--with-xmlid`: indicates that the identifier fields in your client file contains XML_IDs. Typically, use this option if your client file comes from an export.

The complete set of options is described [here](#4-model-skeleton-codes).

## 2.3. Setup the project and review the generated code
1.  **Place client files:**
    * Store your client data files in CSV format within the `origin/` directory.
    * If you have any binary files (e.g., images, documents), place them in the `origin/binary/` directory.

2.  **Verify the client file name:**
    * Open the `files.py` file.
    * Check if the client file is named according to the following convention: the model name with dots (`.`) replaced by underscores (`_`).
        * For example, if your model is `my.model`, the corresponding CSV file should be named `my_model.csv`.
    * If the file is already named correctly, no changes are needed.

    ```python
    # Model my.model
    src_my_model = os.path.join(data_src_dir, 'my_model.csv')
    ```
    
   * Review the python script _my_model.py_. In the generated code, you should at least:   
     * verify the column names. By default their name is the same as the field, which is probably not correct for all columns of the client file. When the tag 'CSV_COLUMN' appears, you also have to replace it by the right column name,
     * apply the right date formats, if any. You always need to replace the tag 'CSV_DATE_FORMAT' with the [directives](https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior) reflecting the field format in your client file,
     * comment or remove the fields you don't need.
        ```python
        mapping_my_model = {
        # ID (#2841): stored, optional, readonly, integer
        'id': mapper.m2o_map(PREFIX_MY_MODEL, mapper.concat('_', 'CSV_COLUMN1','CSV_COLUMN2')),
        # Company (#2851): stored, required, many2one -> res.company - with xml_id in module(s): base(1)
        # DEFAULT: 1
        'company_id/id': mapper.m2o(PREFIX_RES_COMPANY, 'company_id'),
        # Date of Transfer (#2832): stored, optional, readonly, datetime
        'date_done': mapper.val('date_done', postprocess=lambda x: datetime.strptime(x, 'CSV_DATE_FORMAT').strftime('%Y-%m-%d 00:00:00')),
        ```
    
      * By default the delimiter of your CSV file is set to a semicolon ';'. If you use another delimiter you need to change it at the line:

        ```python
        processor = Processor(src_my_model, delimiter=';', preprocess=preprocess_MyModel)
        ```
   * All other project files are automatically set up. Although it's always advised to review:
     * `mapping.py` if you used the option **--map-selection**,
     * `prefix.py` if you import boolean fields or if you didn't use the option **--with-xmlid**,
     * the transform script `transform.sh` (`transform.cmd` on Windows) and the load script `load.sh` (`load.cmd` on Windows) to be sure that all shell commands you need will be launched.
        
        See the options **[--map-selection](#map-selection)** and  **[-a | --append](#append)** for more details.

## 2.4. Repeat steps 2.2 and 2.3 for all models and client files you need to process.

## 2.5. Launch the transformation script

This step transforms the client files from the `origin/` directory into Odoo import files in the `data/` directory. This process does not import any data into the database.

To execute the transformation:

* On Windows, run:

    ```batch
    transform.cmd
    ```

* On other platforms (e.g., Linux, macOS), run:

    ```bash
    ./transform.sh
    ```

After running the script, review the log files `transform_my_model_out.log` and `transform_my_model_err.log` located in the `log/` directory.

* In a successful transformation, the `transform_my_model_err.log` files will be empty.
* The `data/` directory should contain all the destination files specified in `files.py`. For example:

    ```python
    # Model my.model
    dest_my_model = os.path.join(data_dest_dir, 'my.model.csv')
    ```

## 2.6. Launch the load script

This step imports the files from the folder `data/` into the database  as described in the file `conf/connection.conf`.

* On Windows, run:

    ```batch
    load.cmd
    ```
* On other platforms (e.g., Linux, macOS), run:

    ```bash
    ./load.sh
    ```
Check the log files _load_my_model_out.log_ and _load_my_model_err.log_ in the folder `log/`.

>**Note:** On Windows, the log files could reveal some errors but actually there are not.

For each model, the files _my.model.csv.fail_ and _my.model.csv.fail.bis_ are created in the folder `data/`. At the end of the load, the files _.fail.bis_ contain rejected records that need your attention. If these files are empty, it means all the data was imported.

Run ```odoo_dataflow_scaffold.py --help``` for all options.

## 3. Project Structure

The project's directory structure is established using the `-s | --scaffold` option. This creates the necessary directories and project files within the location specified by the `-p | --path` option. If no path is provided, the current directory is used.

### 3.1. Directories and Files

The following directories and files are created:

* `conf/`: This directory contains connection configuration files:
    * `connection.conf`: The default configuration file for RPC calls.
    * `connection.local`: A preset for importing data into a local database.
    * `connection.staging`: A preset for importing data into a staging database (uses encrypted connections).
    * `connection.master`: A preset for importing data into the master database (uses encrypted connections).
* `origin/`: This directory stores the original client files in CSV format.
* `origin/binary/`: This directory stores any binary files associated with the client data (e.g., images, documents).
* `data/`: This directory stores the transformed files ready for import, generated after running the transformation script.
* `log/`: This directory stores log files generated by the transformation and load scripts.
* `transform.sh | .cmd`: This script executes all data transformations.
* `cleanup_data_dir.sh | .cmd`: This script resets the `data/` directory before each new transformation process.
* `load.sh | .cmd`: This script executes all data imports into the Odoo database.
* `files.py`: This file defines the source client files and the destination files to be imported.
* `prefix.py`: This file defines external ID prefixes (corresponding to module names) and any project-specific constants.
* `funclib.py`: This file contains commonly used functions.
* `mapping.py`: This file contains common mapping dictionaries used in data transformations.
* `clean_data.py`: This script is used to remove imported data from the Odoo database.
* `install_lang.py`: This script installs the languages defined in `prefix.py` within the Odoo database.
* `install_modules.py`: This script installs specified Odoo modules.
* `uninstall_modules.py`: This script uninstalls specified Odoo modules.
* `init_map.py`: This file provides a skeleton script for initializing model mappings.

>**Note:** All shell scripts are named with the `.cmd` extension on Windows and the `.sh` extension on other operating systems (e.g., Linux, macOS).

### 3.2. Scaffolding Options

The following options further configure the connection files during the scaffolding process:

* When the `-d | --db` and `-t | --host` options are provided, the database name and hostname are stored in both the `connection.local` and `connection.conf` files. The default hostname is `localhost`, and the default database user credentials are `admin/admin`.
* The default user ID for RPC calls is `2`. You can change this using the `-u | --userid` option.
* The `connection.local` and ` configured to establish encrypted connections when you specify a remote host. Connections remain unencrypted only when the database is located on `localhost`.
* Scaffolding in an existing path preserves any existing files and directories. To overwrite them, use the `-f | --force` option.


# 4. Model Skeleton Codes

This function works with the option **-m | --model**. It generates a python script with all the necessary instructions to apply transformations on one client file and to import the result into one model.

The model definition is fetched by RPC calls using the connection parameters defined in the file `conf/connection.conf` by default. You can select another connection file with the option **-c | --config**.

The skeleton code contains mainly a mapping dictionnary with all the fields assigned to a suited mapper according to their type.

## 4.1. Skeleton Types

You can alter the generated code mapping the fields with the option **-k |  --skeleton**:
* -k |  --skeleton **dict** (default): generates a mapping dictionary suited for transformations fully handled by the mapper function.

```python
mapping_my_model =  {
    'char_field1': mapper.val('char_field1'),
    'integer_field2': mapper.num('integer_field2'),
    ...
}
```
* -k |  --skeleton **map**: generates a mapping dictionary with a map function for each field, which is more handy when some columns of the client file need more complex transformations. By default, the created map functions do nothing more than the original mappers used with **dict**.

```python
def handle_my_model_char_field1(line):
    return mapper.val('char_field1')(line)

def handle_my_model_integer_field2(line):
    return mapper.num('integer_field2')(line)

mapping_my_model =  {
    'char_field1': handle_my_model_char_field1,
    'integer_field2': handle_my_model_integer_field2,
    ...
}
```
In both skeleton types, the default columns name can be chosen between the technical or the user field name in Odoo with option **--field-name tech** or **--field-name user**.

The first displayed field is always the "id" field, then the required ones, then the optional ones, both sorted by name. Their map functions, if any, follow the same order.

You can use the option **-n | --offline** to get a skeleton code without field. 

```python
mapping_my_model =  {
    'id': ,
}
```
This way you keep the benefits of the basic skeleton and the automatic integration of your new script in the project. But you're not annoyed with a lot of fields you probably don't need.  

>**Note:** You may also consider the option [**-r | --required**](#required).

The offline mode is automatically set when no database is provided. When working offline, all functions based on the fields definition are deactivated.

## 4.2. Fields Selection

 You can exclude the non stored fields with the option **--stored**. It is usually advisable but it avoids to import through non stored inherited fields.
 
 One2many and metadata fields are excluded by default but they can be included respectively with the options **--with-o2m** and **--with-metadata**. 


## 4.3. Fields Information

To provide helpful context, each field in the generated skeleton code includes the following properties as comments:

* **id:** The field's unique identifier.
* **type:** The field's data type (e.g., integer, char, many2one).
* **required:** Indicates if the field is mandatory.
* **readonly:** Indicates if the field can be modified.
* **related:** Indicates if the field is a related field and from which model.
* **stored:** Indicates if the field is stored in the database.
* **selection values:** For selection fields, lists the available options.
* **default value:** The field's default value.
* **tracking options:** Information about field change tracking.
* **relationship:** Details of relationships with other models (e.g., many2one target model).
* **computing:** Details about how the field's value is computed.

Displaying these properties removes the need to use an external tool to check field definitions. For `many2one` fields, the code also summarizes the available XML IDs in the related model, showing the count of XML IDs for each module. This helps to efficiently locate and reuse existing external IDs.

To enhance readability, long default values or compute methods are shortened to the first 10 lines. When this occurs, the tag `[truncated]` is appended to indicate the partial display. You can modify this limit using the `--max-descr` option followed by the desired number of lines. Setting the value to `-1` displays the full description.

Example:

```python
# State (#969): stored, optional, many2one -> res.country.state - with xml_id in module(s): base(645)
'state_id/id': mapper.m2o(PREFIX_RES_COUNTRY_STATE, 'state_id'),

# Sales Order (#5305): stored, required, selection
# SELECTION: 'no-message': No Message, 'warning': Warning, 'block': Blocking Message, 
# DEFAULT: no-message
'sale_warn': mapper.val('sale_warn'),

# Rml header (#1069): stored, required, text
# DEFAULT: 
# 
# <header>
#  <pageTemplate>
# [truncated...]
'rml_header': mapper.val('rml_header'),
```    

## 4.4. Other Skeleton Options

<a id=map-selection></a>The option **--map-selection** it to use when the client file contains custom values for selection fields instead of their technical values. To do so, a mapping dictionary is added in the file `mapping.py` with all the possible field values. These are mapped from their visible values by defaut. In addition, the mapper of this field is automatically set to that dictionary. This is done for all selection fields of the model.

Example on the model _res.partner_ and the field _sale_warn_:

`mapping.py`
```python
res_partner_sale_warn_map = {
    "No Message": 'no-message',
    "Warning": 'warning',
    "Blocking Message": 'block',
}
```
`res_partner.py`
```python
mapping_res_partner = {
    ...
    # Sales Order (#5305): stored, required, selection
    # SELECTION: 'no-message': No Message, 'warning': Warning, 'block': Blocking Message
    # DEFAULT: no-message
    'sale_warn': mapper.map_val('sale_warn', res_partner_sale_warn_map),
    ...
```

This option should be called only one time per model. If you use it twice, you must remove manually the duplicate dictionaries  from the file `mapping.py`.

The option **--with-xmlid** is to use when the client file contains ready to use external IDs in identifier fields. In this case no XML_ID prefix is added in the file `prefix.py`, and the mapper of the "id" and relation fields is adapted to take their value strictly from the client file column.

Here is a sample of the default mapping, without option **--with-xmlid**.
```python
'id': mapper.m2o_map(OBJECT_XMLID_PREFIX, mapper.concat('_', 'CSV_COLUMN1','CSV_COLUMN2')),
'field_id/id': mapper.m2o(NEW_XMLID_PREFIX, 'field_id'),
```
Now with **--with-xmlid**.
```python
'id': mapper.val('id'),
'field_id/id': mapper.val('field_id'),
```

<a id=required></a>With the option **-r | --required**, all the skeleton code related to optional fields is commented. It's handy when you have a few fields to import into a model that has a lot. You still have all the fields described, but you don't need to (un)comment or remove lots of them. 
>**Note:** Some fields are always commented because they should not be imported. It's namely the case with related stored, computed and non stored (and non related) fields.

At the end of the skeleton code stands the command line that launches a transformation to one import file (here: _dest_my_model_).
```python
processor.process(mapping_my_model, dest_my_model, {'model': 'my.model', 'context': "{'some_key': True|False}", 'groupby': '', 'worker': 1, 'batch_size': 10}, 'set', verbose=False)
```
This line is preset with some options: _groupby_, _worker_ and _batch_size_ you may want to change. By default, no context is provided, letting the import script from odoo_csv_tools (_odoo_import_thread.py_) manage a default one. Meanwhile, under certain conditions, a context is prefilled here with: 
* **'tracking_disable': True** if a tracked field was found in the model.
* **'defer_fields_computation': True** if a computed field was found in the model.
* **'write_metadata': True** if the option _--with-metadata_ was used _(and even if there is no audit fields)_.

By default, the generated python script is located in the current path and named as the model with dots '.' replaced by underscores '_' (my.model -> my_model.py). You can set another file name (and location) with the option **-o | --outfile**.

<a id=append></a>When a model is added to the project, the needed references can be automatically added in `files.py`, `prefixes.py`, `clean_data.py`, the transform and the load scripts with the option **-a | --append**. 

* In `files.py`: the names of the client file and the import file.
    ```python
    # Model my.model
    src_my_model = os.path.join(data_src_dir, 'my_model.csv')
    dest_my_model = os.path.join(data_src_dir, 'my.model.csv')
    ```
* In `prefix.py`: the XML_ID prefix of the generated model. This prefix is combined with a _project_name_ that is set by default to the last folder of your project_path.
    ```python
    PREFIX_MY_MODEL = '%s_my_model' % project_name
    ```
* In the transfom script: the command line to launch the new transformation.

* On Windows, run:

    ```batch
    echo Transform my_model
    python my_model.py > %LOGDIR%\transform_my_model_out.log 2> %LOGDIR%\transform_my_model_err.log
    ```
* On other platforms (e.g., Linux, macOS), run:
    ```bash
    load_script my_model
    ```
* In the load script: the command line to launch the new import.

* On Windows, run:

    ```batch
    echo Load my_model
    call my_model.cmd > %LOGDIR%\load_my_model_out.log 2> %LOGDIR%\load_my_model_err.log
    ```
* On other platforms (e.g., Linux, macOS), run:
    ```bash
    load_script my_model
    ```

The option **-a | --append** should be used only one time per model. If you use it twice, you must remove manually the duplicate references in all these files.

The skeleton code is preserved if its python script already exists. You can recreate the script with the option **-f | --force**.

> **Note:** this option is only related to the current functions: project scaffolding and/or model skeletoning. If you "--force" the generation of a model without scaffolding the project, only the skeleton code is recreated while the project structure is left as is. In the same way, if you "--force" the scaffolding without the option _-m|--model_, the skeleton codes are preserved if any.

# 5. Command Line Tricks

It is possible to scaffold the project structure and to generate the first skeleton code in one command line. You can only do that with a database where the default credentials _admin/admin_ are valid for the userid. Also, if the database is not on your local computer, encrypted connections must be allowed on port 443.
 
```bash
odoo_dataflow_scaffold.py -s -p project_dir -d my_db -t my_db.odoo.com -m my.model -a
```

 It is possible to reduce the command line. If the option **-t | --host** is used without **-d | --db**, the database will be the first part of the hostname. So, this command line is equivalent to the previous one.

```bash
 odoo_dataflow_scaffold.py -s -p project_dir -t my_db.odoo.com -m my.model -a
 ```
 
 When no option is used, you are prompted to scaffold a project in your current directory. This path can be changed with the only option **-p | --path** So a project can be quickly scaffolded into your working directory with the command:
 
 ```bash
 odoo_dataflow_scaffold.py
 ```
or in another directory with the command:
 ```bash
 odoo_dataflow_scaffold.py -p project_dir
 ```

# 6. How-To
* To quickly create a new project:
```bash
odoo_dataflow_scaffold.py -s -p my_project   
```
Assuming the file `conf/connection.conf` is valid and you are in the project folder.
* To generate a new model:
```bash
odoo_dataflow_scaffold.py -m my.model -a   
```
* To generate a new model without adding its references to the python and action scripts (_say, you just need the mapping code to integrate in an existing script_):
```bash
odoo_dataflow_scaffold.py -m my.model
```
* To only add the references of an already generated model (_because you previously omitted the option -a_):
```bash
odoo_dataflow_scaffold.py -m my.model -a
```
* To change the skeleton of an already generated model (YOUR CHANGES IN THE PYTHON SCRIPT WILL BE LOST !!!):

    Change some options between brackets []:
    ```bash
    odoo_dataflow_scaffold.py -m my.model -f [-k dict|map] [-r] [--map-selection] [--max-descr MAXDESCR] [--with-xmid] [--with_o2m] [--with-metadata] [--stored]
    ```
    Generate a minimal skeleton (offline mode):
    ```bash
    odoo_dataflow_scaffold.py -m my.model -f -n
    ```
* To list all the models from the target Odoo instance:
```bash
odoo_dataflow_scaffold.py -l
```

# 7. Requirements
## 7.1. On your local computer
* [odoo-data-flow](https://github.com/OdooDataFlow/odoo-data-flow) Install it with the command:

    `[sudo] pip install odoo-data-flow`

## 7.2. On the target database
* The module [product_template_attribute_xmlid](https://github.com/OdooDataFlow/addons) must be installed to allow manual product.product creation.


# 8. Known Issues

* The option **-a | --append** adds the model references event if they already exist in their respective files (`prefix.py`, `clean_data.py`).
* With the option **--map-selection**, the mapping dictionaries of the selection fields are added even they already exist in `mapping.py`.
