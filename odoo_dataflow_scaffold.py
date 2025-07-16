#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import configparser
import io
import os
import platform
import re
import socket
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List

from odoo_data_flow.lib import conf_lib

module_version = "1.4.3"
offline = False
dbname = ""
hostname = ""
force = False
data_dir_name = "data"
log_dir_name = "log"
conf_dir_name = "conf"
orig_dir_name = "origin"
project_name = ""
model_mapped_name = ""
selection_sep = ": "
script_extension = ".cmd" if platform.system() == "Windows" else ".sh"
default_python_exe = ""
default_path = ""
csv_delimiter = ";"
base_dir = Path(".")
has_tracked_fields = False
has_computed_fields = False
model = ""
userid = 2
config = ""
outfile = ""
required = False
skeleton = ""
wstored = False
wo2m = False
wmetadata = False
mapsel = False
wxmlid = False
maxdescr = 10
append = False
verbose = False
fieldname = ""
conf_dir = ""
orig_dir = ""
orig_raw_dir = ""
data_dir = ""
log_dir = ""
model_class_name = ""
model_mapping_name = ""


##############################################################################
# FUNCTIONS FOR DIRECTORY STRUCTURE
##############################################################################


def create_folder(path: Path) -> None:
    """Create a folder only if it doesn't exist or if the flag "force" is set.

    Args:
        path: The path of the folder to create.
    """
    if path.exists() and not force:
        sys.stdout.write(f"Folder {path} already exists.\n")
        return

    sys.stdout.write(f"Create folder {path}\n")
    path.mkdir(parents=True, exist_ok=True)


def check_file_exists(func: Callable) -> Callable:
    """Decorator avoiding to overwrite a file if it already exists
    but still allowing it if the flag "force" is set.

    Args:
        func: The function to decorate.

    Returns:
        The decorated function.
    """

    def wrapper(*args, **kwargs):
        file_path = Path(args[0])
        if file_path.is_file() and not force:
            sys.stdout.write(f"File {file_path} already exists.\n")
            return
        sys.stdout.write(f"Create file {file_path}\n")
        func(*args, **kwargs)

    return wrapper


def is_remote_host(hostname: str) -> bool:
    """Return True if 'hostname' is not the local host.

    Args:
        hostname: The hostname to check.

    Returns:
        True if the hostname is remote, False otherwise.
    """
    my_host_name = socket.gethostname()
    my_host_ip = socket.gethostbyname(my_host_name)
    if any(
        hostname in x
        for x in [
            my_host_name,
            my_host_ip,
            socket.getfqdn(),
            "localhost",
            "127.0.0.1",
        ]
    ):
        return False
    return True


@check_file_exists
def create_connection_file(
    file: Path, host: str, dbname: str, userid: int
) -> None:
    """Create a connection file.

    Enforce encrypted connection on remote hosts.
    Leave unencrypted for local databases.
    """
    is_remote = is_remote_host(host)
    protocol = "jsonrpcs" if is_remote else "jsonrpc"
    port = "443" if is_remote else "8069"
    with file.open("w", encoding="utf-8") as f:
        f.write("[Connection]\n")
        f.write(f"hostname = {host}\n")
        f.write(f"database = {dbname}\n")
        f.write("login = admin\n")
        f.write("password = admin\n")
        f.write(f"protocol = {protocol}\n")
        f.write(f"port = {port}\n")
        f.write(f"uid = {userid}\n")


@check_file_exists
def create_cleanup_script(file: Path) -> None:
    """Create the shell script to empty the folder "data".

    Args:
        file: The path to the cleanup script.
    """
    if platform.system() == "Windows":
        with file.open("w", encoding="utf-8") as f:
            f.write("@echo off\n\n")
            f.write(f"set DIR={data_dir_name}\n")
            f.write("del /F /S /Q %DIR%\\*\n")
    else:
        with file.open("w", encoding="utf-8") as f:
            f.write("#!/usr/bin/env bash\n\n")
            f.write(f"DIR={data_dir_name}/\n")
            f.write("rm -rf --interactive=never $DIR\n")
            f.write("mkdir -p $DIR\n")
        file.chmod(0o755)


@check_file_exists
def create_transform_script(file: Path) -> None:
    """Create the shell script skeleton that launches all transform commands.

    Args:
        file: The path to the transform script.
    """
    if platform.system() == "Windows":
        with file.open("w", encoding="utf-8") as f:
            f.write("@echo off\n\n")
            f.write(f"set LOGDIR={log_dir_name}\n")
            f.write(f"set DATADIR={data_dir_name}\n\n")
            f.write("call cleanup_data_dir.cmd\n\n")
            f.write("REM Add here all transform commands\n")
            f.write(
                "REM python my_model.py > %LOGDIR%\\transform_$1_out.log 2> %LOGDIR%\\transform_$1_err.log\n"
            )
    else:
        with file.open("w", encoding="utf-8") as f:
            f.write("#!/usr/bin/env bash\n\n")
            f.write("# Use all available CPU cores for Polars operations\n")
            f.write("export POLARS_MAX_THREADS=$(nproc)\n\n")
            f.write(f"LOGDIR={log_dir_name}\n")
            f.write(f"DATADIR={data_dir_name}\n\n")
            f.write("COLOR='\\033[1;32m'\n")
            f.write("NC='\\033[0m'\n\n")
            f.write("msg() {\n")
            f.write("    start=$(date +%s.%3N)\n")
            f.write("    PID=$!\n")
            f.write('    printf "($PID) Transform ${COLOR}$1${NC} ["\n')
            f.write("    while kill -0 $PID 2> /dev/null; do\n")
            f.write('        printf  "▓"\n')
            f.write("        sleep 1\n")
            f.write("    done\n")
            f.write("    end=$(date +%s.%3N)\n")
            f.write(
                "    runtime=$(python -c \"print(f'{int(float(end) - float(start))/60}:{int(float(end) - float(start))%60:02}')\")\n"
            )
            f.write('    printf "] $runtime \\n"\n')
            f.write("}\n\n")
            f.write("load_script() {\n")
            f.write("    #rm -f $DATADIR/*$1*.csv*\n")
            f.write("    rm -f $LOGDIR/transform_$1_*.log\n")
            f.write(
                "    python $1.py > $LOGDIR/transform_$1_out.log 2> $LOGDIR/transform_$1_err.log &\n"
            )
            f.write('    msg "$1"\n')
            f.write("}\n\n")
            f.write("./cleanup_data_dir.sh\n\n")
            f.write("# Add here all transform commands\n")
            f.write("# python my_model.py\n")
            f.write("# load_script python_script (without extension)\n")
            f.write("chmod +x *.sh\n")
        file.chmod(0o755)


@check_file_exists
def create_load_script(file: Path) -> None:
    """Create the shell script skeleton that launches all load commands.

    Args:
        file: The path to the load script.
    """
    if platform.system() == "Windows":
        with file.open("w", encoding="utf-8") as f:
            f.write("@echo off\n\n")
            f.write(f"set LOGDIR={log_dir_name}\n\n")
            f.write("REM Add here all load commands\n")
            f.write(
                "REM my_model.cmd > %LOGDIR%\\load_$1_out.log 2> %LOGDIR%\\load_$1_err.log\n"
            )
    else:
        with file.open("w", encoding="utf-8") as f:
            f.write("#!/usr/bin/env bash\n\n")
            f.write(f"LOGDIR={log_dir_name}\n\n")
            f.write("COLOR='\\033[1;32m'\n")
            f.write("NC='\\033[0m'\n\n")
            f.write("user_interrupt() {\n")
            f.write('    echo -e "\\n\\nKeyboard Interrupt detected."\n')
            f.write('    echo -e "\\nKill import tasks..."\n')
            f.write("    # Kill the current import\n")
            f.write("    killall odoo-import-thread.py\n")
            f.write("    sleep 2\n")
            f.write("    # Kill the next launched import (--fail)\n")
            f.write("    killall odoo-import-thread.py\n")
            f.write("    exit\n")
            f.write("}\n\n")
            f.write("msg() {\n")
            f.write("    start=$(date +%s.%3N)\n")
            f.write("    PID=$!\n")
            f.write('    printf "($PID) Load ${COLOR}$1${NC} ["\n')
            f.write("    while kill -0 $PID 2> /dev/null; do\n")
            f.write('        printf  "▓"\n')
            f.write("        sleep 1\n")
            f.write("    done\n")
            f.write("    end=$(date +%s.%3N)\n")
            f.write(
                "    runtime=$(python -c \"print(f'{int(float(end) - float(start))/60}:{int(float(end) - float(start))%60:02}')\")\n"
            )
            f.write('    printf "] $runtime \\n"\n')
            f.write("}\n\n")
            f.write("load_script() {\n")
            f.write("    # rm -f $LOGDIR/load_$1_*.log")
            f.write(
                "    ./$1.sh > $LOGDIR/load_$1_out.log 2> $LOGDIR/load_$1_err.log &\n"
            )
            f.write('    msg "$1"\n')
            f.write("}\n\n")
            f.write("trap user_interrupt SIGINT\n")
            f.write("trap user_interrupt SIGTSTP\n\n")
            f.write("# Add here all load commands\n")
            f.write("# load_script shell_script (without extension)\n")
        file.chmod(0o755)


@check_file_exists
def create_file_prefix(file: Path) -> None:
    """Create the skeleton of prefix.py.

    Args:
        file: The path to the prefix.py file.
    """
    with file.open("w", encoding="utf-8") as f:
        f.write("# -*- coding: utf-8 -*-\n\n")
        f.write(
            "# This file defines xml_id prefixes and projectwise variables.\n\n"
        )
        f.write("# Defines here a identifier used in the created XML_ID.\n")
        f.write(f"project_name = '{project_name}'\n")
        f.write("\n")
        f.write("DEFAULT_WORKER = 1\n")
        f.write("DEFAULT_BATCH_SIZE = 20\n")
        f.write("\n")
        f.write("# CONSTANTS\n")
        f.write("COMPANY_ID = 'base.main_company'\n")
        f.write("\n")
        f.write(
            "# Define here all values in client files considered as TRUE value.\n"
        )
        f.write(
            "true_values = ['TRUE', 'True', 'true', 'YES', 'Yes', 'yes', 'Y', 'y', '1', '1,0', '1.0']\n"
        )
        f.write(
            "# Define here all values in client files considered as FALSE value.\n"
        )
        f.write(
            "false_values = ['FALSE', 'False', 'false', 'NO', 'No', 'no', 'N', 'n', '0', '0,0', '0.0']\n"
        )
        f.write("\n")
        f.write("# Define the languages used in the import.\n")
        f.write("# These will be installed by calling install_lang.py\n")
        f.write("# Key: language code used in the client file\n")
        f.write("# Value: the Odoo lang code\n")
        f.write("res_lang_map = {\n")
        f.write("#    'E': 'en_US',\n")
        f.write("}\n\n")
        f.write("# XML ID PREFIXES\n")


@check_file_exists
def create_file_mapping(file: Path) -> None:
    """Create the skeleton of mapping.py.

        Use odoo_import_scaffold with option --map-selection to
        automatically build dictionaries of selection fields.

    Args:
        file: The path to the mapping.py file.
    """
    with file.open("w", encoding="utf-8") as f:
        f.write("# -*- coding: utf-8 -*-\n\n")
        f.write("# This file defines mapping dictionaries.\n\n")
        f.write("# MAPPING DICTIONARIES\n")
        f.write("# Use odoo_import_scaffold with option --map-selection to\n")
        f.write("# automatically build dictionaries of selection fields.\n\n")


@check_file_exists
def create_file_files(file: Path, source_config: str, dest_config: str) -> None:
    """Create the skeleton of files.py."""
    with file.open("w", encoding="utf-8") as f:
        f.write("# -*- coding: utf-8 -*-\n\n")
        f.write("# This file defines the names of all used files.\n\n")
        f.write("from pathlib import Path\n\n")
        f.write("# Folders\n")
        f.write(f"conf_dir = Path('{conf_dir_name}')\n")
        f.write(f"data_src_dir = Path('{orig_dir_name}')\n")
        f.write("data_raw_dir = data_src_dir / 'binary'\n")
        f.write(f"data_dest_dir = Path('{data_dir_name}')\n\n")
        f.write("# Configuration\n")
        f.write(f"source_config_file = conf_dir / '{source_config}'\n")
        f.write(f"destination_config_file = conf_dir / '{dest_config}'\n\n")
        f.write("# Declare here all data files\n")

        if not model:
            f.write(
                "# Client file: src_my_model = data_src_dir / 'my_model.csv'\n"
            )
            f.write(
                "# Import file: dest_my_model = data_dest_dir / 'my.model.csv'\n"
            )

        f.write("\n")


@check_file_exists
def create_file_lib(file: Path) -> None:
    """Create the skeleton of funclib.py.

    Args:
        file: The path to the funclib.py file.
    """
    with file.open("w", encoding="utf-8") as f:
        f.write("# -*- coding: utf-8 -*-\n\n")
        f.write("# This file defines common functions.\n\n")
        f.write("from odoo_data_flow.lib import mapper\n")
        f.write("from odoo_data_flow.lib.transform import Processor\n")
        f.write("from prefix import *\n")
        f.write("from mapping import *\n")
        f.write("from datetime import datetime\n")
        f.write("\n\n")
        f.write("nvl = lambda a, b: a or b\n")
        f.write("\n\n")
        f.write("def keep_numbers(val: str) -> str:\n")
        f.write("    return ''.join(filter(str.isdigit, val))\n")
        f.write("\n\n")
        f.write("def keep_letters(val: str) -> str:\n")
        f.write("    return ''.join(filter(str.isalpha, val))\n")
        f.write("\n\n")
        f.write(
            "# For more complex cases, consider using the `unidecode` library.\n"
        )
        f.write("def remove_accents(val: str) -> str:\n")
        f.write("    return val\n")
        f.write("\n\n")
        f.write("def keep_column_value(val, column):\n")
        f.write("    def keep_column_value_fun(line):\n")
        f.write("        if line[column] != val:\n")
        f.write(
            '            raise SkippingException(f"Column {column} with wrong value {val}")\n'
        )
        f.write("        return line[column]\n")
        f.write("    return keep_column_value_fun\n")
        f.write("\n")


@check_file_exists
def create_file_clean_data(file: Path) -> None:
    """Create the skeleton of clean_data.py.

    Args:
        file: The path to the clean_data.py file.
    """
    with file.open("w", encoding="utf-8") as f:
        f.write("# -*- coding: utf-8 -*-\n\n")
        f.write("# This script remove the data created by the import.\n\n")
        f.write("import odoolib\n")
        f.write("from odoo_data_flow.lib import conf_lib\n")
        f.write("from prefix import *\n")
        f.write("from files import *\n\n")
        f.write(
            "connection = conf_lib.get_connection_from_config(config_file)\n\n"
        )
        f.write(
            "def delete_model_data(connection, model, demo: bool = False) -> None:\n"
        )
        f.write("    model_model = connection.get_model(model)\n")
        f.write("    record_ids = model_model.search([])\n")
        f.write("    if demo:\n")
        f.write(
            "        print(f'Will remove {len(record_ids)} records from {model}')\n"
        )
        f.write("    else:\n")
        f.write(
            "        print(f'Remove {len(record_ids)} records from {model}')\n"
        )
        f.write("        model_model.unlink(record_ids)\n")
        f.write("\n\n")
        f.write(
            "def delete_xml_id(connection, model, module, demo: bool = False) -> None:\n"
        )
        f.write("    data_model = connection.get_model('ir.model.data')\n")
        f.write(
            "    data_ids = data_model.search([('module', '=', module), ('model', '=', model)])\n"
        )
        f.write("    records = data_model.read(data_ids, ['res_id'])\n")
        f.write("    record_ids = [rec['res_id'] for rec in records]\n")
        f.write("    if demo:\n")
        f.write(
            "        print(f'Will remove {len(record_ids)} xml_id {module} from {model}')\n"
        )
        f.write("    else:\n")
        f.write(
            "        print(f'Remove {len(record_ids)} xml_id {module} from {model}')\n"
        )
        f.write("        connection.get_model(model).unlink(record_ids)\n")
        f.write("\n\n")
        f.write("demo = True\n\n")


@check_file_exists
def create_file_install_lang(file: Path) -> None:
    """Create the skeleton of install_lang.py.

    Args:
        file: The path to the install_lang.py file.
    """
    with file.open("w", encoding="utf-8") as f:
        f.write("# -*- coding: utf-8 -*-\n\n")
        f.write("import odoolib\n")
        f.write("from prefix import *\n")
        f.write("from files import *\n")
        f.write("from odoo_data_flow.lib import conf_lib\n\n")
        f.write(
            "connection = conf_lib.get_connection_from_config(config_file)\n\n"
        )
        f.write(
            "model_lang = connection.get_model('base.language.install')\n\n"
        )
        f.write("for key in res_lang_map.keys():\n")
        f.write("    lang = res_lang_map[key]\n")
        f.write("    res = model_lang.create({'lang': lang})\n")
        f.write("    model_lang.lang_install(res)\n")


@check_file_exists
def create_file_install_modules(file: Path) -> None:
    """Create the skeleton of install_modules.py.

    Args:
        file: The path to the install_modules.py file.
    """
    with file.open("w", encoding="utf-8") as f:
        f.write("# -*- coding: utf-8 -*-\n\n")
        f.write("import sys\n")
        f.write("import odoolib\n")
        f.write("from prefix import *\n")
        f.write("from files import *\n")
        f.write("from odoo_data_flow.lib import conf_lib\n")
        f.write(
            "from odoo_data_flow.lib.internal.rpc_thread import RpcThread\n"
        )
        f.write("from files import config_file\n\n")
        f.write(
            "connection = conf_lib.get_connection_from_config(config_file)\n\n"
        )
        f.write("model_module = connection.get_model('ir.module.module')\n")
        f.write("model_module.update_list()\n\n")
        f.write("# Set the modules to install\n")
        f.write("module_names = []\n\n")
        f.write(
            "module_ids = model_module.search_read([['name', 'in', module_names]])\n\n"
        )
        f.write("rpc_thread = RpcThread(1)\n\n")
        f.write("for module in module_ids:\n")
        f.write("    if module['state'] == 'installed':\n")
        f.write(
            "        rpc_thread.spawn_thread(model_module.button_immediate_upgrade, [module['id']])\n"
        )
        f.write("    else:\n")
        f.write(
            "        rpc_thread.spawn_thread(model_module.button_immediate_install, [module['id']])\n"
        )


@check_file_exists
def create_file_uninstall_modules(file: Path) -> None:
    """Create the skeleton of uninstall_modules.py.

    Args:
        file: The path to the uninstall_modules.py file.
    """
    with file.open("w", encoding="utf-8") as f:
        f.write("# -*- coding: utf-8 -*-\n\n")
        f.write("import sys\n")
        f.write("import odoolib\n")
        f.write("from prefix import *\n")
        f.write("from files import *\n")
        f.write("from odoo_data_flow.lib import conf_lib\n")
        f.write(
            "from odoo_data_flow.lib.internal.rpc_thread import RpcThread\n"
        )
        f.write("from files import config_file\n\n")
        f.write(
            "connection = conf_lib.get_connection_from_config(config_file)\n\n"
        )
        f.write("model_module = connection.get_model('ir.module.module')\n")
        f.write("model_module.update_list()\n\n")
        f.write("# Set the modules to uninstall\n")
        f.write("module_names = []\n\n")
        f.write(
            "module_ids = model_module.search_read([['name', 'in', module_names]])\n\n"
        )
        f.write("rpc_thread = RpcThread(1)\n\n")
        f.write("for module in module_ids:\n")
        f.write("    if module['state'] == 'installed':\n")
        f.write(
            "        rpc_thread.spawn_thread(model_module.button_immediate_uninstall, [module['id']])\n"
        )


@check_file_exists
def create_file_init_map(file: Path) -> None:
    """Create the skeleton of init_map.py.

    Args:
        file: The path to the init_map.py file.
    """
    with file.open("w", encoding="utf-8") as f:
        f.write("# -*- coding: utf-8 -*-\n\n")
        f.write("import odoolib\n")
        f.write("from prefix import *\n")
        f.write("from files import *\n")
        f.write("from odoo_data_flow.lib import conf_lib\n")
        f.write("import json\n")
        f.write("import io\n\n")
        f.write(
            "connection = conf_lib.get_connection_from_config(config_file)\n\n"
        )
        f.write(
            "def build_map_product_category_id(filename: str = '') -> dict:\n"
        )
        f.write(
            "    # Build a dictionary {product_category : xml_id} of all existing product_category.\n"
        )
        f.write("    model_data = connection.get_model('ir.model.data')\n")
        f.write(
            "    model_product_category = connection.get_model('product.category')\n"
        )
        f.write(
            "    recs = model_product_category.search_read([], ['id', 'name'])\n\n"
        )
        f.write("    res_map = {}\n")
        f.write("    for rec in recs:\n")
        f.write(
            "        data = model_data.search_read([('res_id', '=', rec['id']), ('model', '=', 'product.category')], ['module', 'name'])\n"
        )
        f.write("        if len(data):\n")
        f.write("            key = rec['name'].strip()\n")
        f.write(
            "            val = '.'.join([data[0]['module'], data[0]['name'] ])\n"
        )
        f.write("            res_map[key] = val.strip()\n")
        f.write("        # else:\n")
        f.write(
            "        #     print(f'Product category {rec['name']} has no XML_ID (id: {rec['id']})')\n\n"
        )
        f.write("    if filename:\n")
        f.write("        with open(filename, 'w') as fp:\n")
        f.write("            json.dump(res_map, fp)\n\n")
        f.write("    return res_map\n\n")
        f.write("# Execute mapping\n")
        f.write(
            "# dummy = build_map_product_category_id(work_map_product_category_id)\n\n"
        )
        f.write("# Add in files.py\n")
        f.write(
            "# work_map_product_category_id = data_src_dir / 'work_map_product_category_id.json'\n\n"
        )
        f.write("# Add in transformation script\n")
        f.write("# map_product_category_id = {}\n")
        f.write(
            "# with io.open(work_map_product_category_id, 'r', encoding='utf-8') as fp:\n"
        )
        f.write("#     map_product_category_id = json.load(fp)\n\n")
        f.write(
            "# Add in transformation script to map 'id' column. REVIEW COLUNM NAME and PREFIX\n"
        )
        f.write("# def handle_product_category_id(line):\n")
        f.write("#     categ_name = line['Product Category']\n")
        f.write("#     try:\n")
        f.write(
            "#         categ_xml_id = map_product_category_id[categ_name]\n"
        )
        f.write("#     except:\n")
        f.write(
            "#         categ_xml_id = mapper.m2o(PREFIX_PRODUCT_CATEGORY, 'Product Category')(line)\n"
        )
        f.write("#     return categ_xml_id\n\n")
        f.write(
            "##################################################################################################\n\n"
        )
        f.write(
            "def build_account_map(company_id: int, filename: str = '') -> dict:\n"
        )
        f.write(
            "    # Build a dictionary {account_code : xml_id} of all existing accounts of a company.\n"
        )
        f.write("    model_data = connection.get_model('ir.model.data')\n")
        f.write("    model_account = connection.get_model('account.account')\n")
        f.write(
            "    recs = model_account.search_read([('company_id', '=', company_id)], ['id', 'code'])\n\n"
        )
        f.write("    res_map = {}\n")
        f.write("    for rec in recs:\n")
        f.write(
            "        data = model_data.search_read([('res_id', '=', rec['id']), ('model', '=', 'account.account')], ['module', 'name'])\n"
        )
        f.write("        if len(data):\n")
        f.write("            key = rec['code'].strip()\n")
        f.write(
            "            val = '.'.join([data[0]['module'], data[0]['name'] ])\n"
        )
        f.write("            res_map[key] = val.strip()\n")
        f.write("        # else:\n")
        f.write(
            "        #     print(f'Account {rec['code']} has no XML_ID')\n\n"
        )
        f.write("    if filename:\n")
        f.write("        with open(filename, 'w') as fp:\n")
        f.write("            json.dump(res_map, fp)\n\n")
        f.write("    return res_map\n\n")
        f.write("# Execute mapping\n")
        f.write("# dummy = build_account_map(1, work_map_account_code_id)\n\n")
        f.write("# Add in files.py\n")
        f.write(
            "# work_map_account_code_id = data_src_dir / 'work_map_account_code_id.json'\n\n"
        )
        f.write("# Add in transformation script\n")
        f.write("# map_account_code_id = {}\n")
        f.write(
            "# with io.open(work_map_account_code_id, 'r', encoding='utf-8') as fp:\n"
        )
        f.write("#     map_account_code_id = json.load(fp)\n\n")
        f.write(
            "# Add in transformation script to map 'id' column. REVIEW COLUNM NAME and PREFIX\n"
        )
        f.write("# def handle_account_account_id_map(line):\n")
        f.write("#     code = line['Accounts']\n")
        f.write("#     try:\n")
        f.write("#         val = map_account_code_id[code]\n")
        f.write("#     except:\n")
        f.write(
            "#         val = mapper.m2o(PREFIX_ACCOUNT_ACCOUNT, 'Accounts')(line)\n"
        )
        f.write("#     return val\n\n")
        f.write(
            "##################################################################################################\n\n"
        )


def scaffold_dir(
    args: argparse.Namespace, source_config: str, dest_config: str
) -> None:
    """Create the whole directory structure and the basic project files."""
    # If database is omitted, get the first part of the hostname
    if is_remote_host(args.host) and not args.dbname:
        dbname = args.host.split(".")[0]
        sys.stdout.write(f"Database is set by default to {dbname}.\n")
    else:
        dbname = args.dbname

    conf_dir = base_dir / conf_dir_name
    orig_dir = base_dir / orig_dir_name
    conf_dir = base_dir / conf_dir_name
    orig_dir = base_dir / orig_dir_name
    orig_raw_dir = orig_dir / "binary"
    data_dir = base_dir / data_dir_name
    log_dir = base_dir / log_dir_name

    create_folder(Path(conf_dir))
    create_folder(Path(orig_dir))
    create_folder(Path(orig_raw_dir))
    create_folder(Path(data_dir))
    create_folder(Path(log_dir))

    # Create the source connection file
    create_connection_file(
        conf_dir / source_config, args.host, dbname, args.userid
    )

    create_connection_file(
        conf_dir / "local_connection.conf", "localhost", dbname, args.userid
    )
    create_connection_file(
        conf_dir / "staging_connection.conf",
        ".dev.odoo.com",
        dbname,
        args.userid,
    )
    create_connection_file(
        conf_dir / "prod_connection.conf", ".odoo.com", dbname, args.userid
    )

    # If a separate destination is specified, create a placeholder for it
    if source_config != dest_config:
        create_connection_file(
            conf_dir / dest_config,
            "DESTINATION_HOST",
            "DESTINATION_DB",
            args.userid,
        )

    create_cleanup_script(
        Path(base_dir) / f"cleanup_data_dir{script_extension}"
    )
    create_transform_script(Path(base_dir) / f"transform{script_extension}")
    create_load_script(Path(base_dir) / f"load{script_extension}")
    create_file_prefix(Path(base_dir) / "prefix.py")
    create_file_mapping(Path(base_dir) / "mapping.py")
    create_file_files(Path(base_dir) / "files.py", source_config, dest_config)
    create_file_lib(Path(base_dir) / "funclib.py")
    create_file_clean_data(Path(base_dir) / "clean_data.py")
    create_file_install_lang(Path(base_dir) / "install_lang.py")
    create_file_install_modules(Path(base_dir) / "install_modules.py")
    create_file_uninstall_modules(Path(base_dir) / "uninstall_modules.py")
    create_file_init_map(Path(base_dir) / "init_map.py")

    sys.stdout.write(f"Project created in {Path(base_dir).resolve()}\n")


##############################################################################
# FUNCTIONS FOR MODEL SKELETON CODE
##############################################################################


class ModelField:
    """Manages how to get a suited mapper function and how to document itself.

    Args:
        connection: The Odoo connection object.
        properties: A dictionary of field properties.
    """

    def __init__(self, connection: Any, properties: Dict[str, Any]) -> None:
        self.connection = connection
        self.properties = properties
        self.import_warn_msg: List[str] = []
        self.id: int = properties.get("id")
        self.name: str = properties.get("name")
        self.type: str = properties.get("ttype")
        self.required: bool = properties.get("required")
        self.readonly: bool = properties.get("readonly")
        self.string: str = properties.get("field_description")
        self.store: bool = properties.get("store")
        self.track_visibility: str = properties.get("track_visibility")
        self.related: str = properties.get("related")
        self.relation: str = properties.get("relation")
        self.depends: str = properties.get("depends")
        self.compute: List[str] = self._get_compute()
        self.selection: List[str] = self._get_selection()
        self.default_value: List[str] = self._get_default()

        # Reasons avoiding to import a field -> commented by get_info
        if self.related and self.store:
            self.import_warn_msg.append("related stored")
        if not self.store and not self.related:
            self.import_warn_msg.append("non stored")
        if len(self.compute) > 1:
            self.import_warn_msg.append("computed")

    def _get_selection(self) -> List[str]:
        """Fetch the selection values of a field.

        Returns:
            A list of strings "'technical_value': 'visible_value'"
            or an empty list if no selection exists.
        """
        selection_list = []
        model_model = self.connection.get_model(model)
        try:
            vals = (
                model_model.fields_get([self.name])
                .get(self.name)
                .get("selection")
            )
            if not vals:
                return selection_list
            for sel in vals:
                selection_list.append(f"'{sel[0]}'{selection_sep}{sel[1]}")
        except Exception:
            pass
        return selection_list

    def _get_default(self) -> List[str]:
        """Fetch the default value of a field.

        Returns:
            A list of strings (because the default value can be a multiline value)
            or an empty list if no default value exists.
        """
        model_model = self.connection.get_model(model)
        val = model_model.default_get([self.name]).get(self.name, "")
        lines = str(val).splitlines()

        if maxdescr > -1 and len(lines) > max(1, maxdescr):
            lines = lines[:maxdescr] + ["[truncated...]"]

        return lines

    def _get_compute(self) -> List[str]:
        """Fetch the compute method of a field.

        Returns:
            A list of strings (because the compute method is often a multiline value)
            or an empty list if no compute method exists.
        """
        val = self.properties.get("compute")
        lines = str(val).splitlines()

        if maxdescr > -1 and len(lines) > maxdescr:
            lines = lines[:maxdescr] + ["[truncated...]"]

        return lines

    def get_info(self) -> str:
        """Build the complete block of text describing a field.

        Returns:
            A string containing the field information.
        """
        info = f"{self.string} (#{self.id}): {'stored' if self.store else 'non stored'}"
        info += f", {'required' if self.required else 'optional'}"
        if self.readonly:
            info += ", readonly"
        if self.track_visibility:
            info += f", track_visibility ({self.track_visibility})"
        if self.related:
            info += f", related (={self.related})"
        info += f", {self.type}"

        if self.relation:
            info += f" -> {self.relation}"
            # Add XMLID summary in field info
            model_data = self.connection.get_model("ir.model.data")
            external_prefixes = model_data.read_group(
                [("model", "=", self.relation)], ["module"], ["module"]
            )
            if external_prefixes:
                info += " - with xml_id in module(s):"
                for data in external_prefixes:
                    info += f" {data['module']}({data['module_count']})"

        if self.selection:
            info += f"\n    # SELECTION: {', '.join(self.selection)}"

        if self.default_value:
            if len(self.default_value) == 1:
                info += f"\n    # DEFAULT: {self.default_value[0]}"
            else:
                info += f"\n    # DEFAULT: \n    # {'\n    # '.join(self.default_value)}"

        if len(self.compute) > 1:
            info += f"\n    # COMPUTE: depends on {self.depends}\n    # {'\n    # '.join(self.compute)}"

        if self.import_warn_msg:
            info += (
                f"\n    # AVOID THIS FIELD: {', '.join(self.import_warn_msg)}"
            )

        return info

    def get_name(self) -> str:
        """Returns the technical or user-friendly name of the field."""
        return self.name if fieldname == "tech" else self.string

    def get_mapping_name(self) -> str:
        """Return the field name as needed in the import file."""
        return (
            f"{self.name}/id"
            if self.type in ("many2one", "many2many")
            else self.name
        )

    def get_mapper_command(self) -> str:
        """Return a suited mapper function according to the field properties and skeleton options."""
        if self.name == "id":
            if wxmlid:
                return f"mapper.val('{self.name}')"
            else:
                return "mapper.m2o_map(OBJECT_XMLID_PREFIX, mapper.concat('_', 'CSV_COLUMN1','CSV_COLUMN2'))"

        elif self.type in ("integer", "float", "monetary"):
            return f"mapper.num('{self.get_name()}')"
        elif self.type in ("boolean"):
            return f"mapper.bool_val('{self.get_name()}', true_values=true_values, false_values=false_values)"
        elif self.type in ("datetime"):
            return f"mapper.val('{self.get_name()}', postprocess=lambda x: datetime.strptime(x, 'CSV_DATE_FORMAT').strftime('%%Y-%%m-%%d 00:00:00') if x else '')"
        elif self.type in ("binary"):
            return f"mapper.binary('{self.get_name()}', data_raw_dir)"
        elif self.type in ("selection"):
            if mapsel:
                return f"mapper.map_val('{self.get_name()}', {model_mapped_name}_{self.name}_map)"
            else:
                return f"mapper.val('{self.get_name()}')"
        elif self.type in ("many2many") and not wxmlid:
            return f"mapper.m2m(PREFIX_{self.relation.replace('.', '_').upper()}, '{self.get_name()}')"
        elif self.type in ("many2one", "one2many", "many2many") and not wxmlid:
            return f"mapper.m2o(PREFIX_{self.relation.replace('.', '_').upper()}, '{self.get_name()}')"

        else:
            return f"mapper.val('{self.get_name()}')"

    def is_required(self) -> bool:
        """Return True if the field is required and has no default value."""
        return self.required and not self.default_value


def load_fields() -> List[ModelField]:
    """Build the model fields list, fetched as defined in the target database.

    Returns:
        A list of ModelField objects.
    """
    global has_tracked_fields
    global has_computed_fields
    has_tracked_fields, has_computed_fields = False, False
    connection = conf_lib.get_connection_from_config(config)
    model_fields = connection.get_model("ir.model.fields")

    field_ids = model_fields.search([("model", "=", model)])
    fields = model_fields.read(field_ids)
    ret = []
    for field in fields:
        f = ModelField(connection, field)
        has_tracked_fields = has_tracked_fields or bool(f.track_visibility)
        has_computed_fields = has_computed_fields or len(f.compute) > 1
        ret.append(f)
    return ret


def write_begin(file: io.TextIOWrapper) -> None:
    """Write the beginning of the generated python script.

    Args:
        file: The file object to write to.
    """
    file.write("# -*- coding: utf-8 -*-\n")
    file.write("import polars as pl\n")
    file.write("\n")
    file.write("from odoo_data_flow.lib import mapper\n")
    file.write("from odoo_data_flow.lib.transform import Processor\n")
    file.write("from prefix import *\n")
    file.write("from mapping import *\n")
    file.write("from files import *\n")
    file.write("from funclib import *\n")
    file.write("from datetime import datetime\n")
    file.write("\n")
    file.write("# Needed for RPC calls\n")
    file.write("# import odoolib\n")
    file.write("# from odoo_data_flow.lib import conf_lib\n")
    file.write(
        "# connection = conf_lib.get_connection_from_config(source_config_file)\n"
    )
    file.write(f"def preprocess_{model_class_name}(header, data):\n")
    file.write("    # Do nothing\n")
    file.write("    return header, data\n")
    file.write("    #\n")
    file.write("    # Add a column\n")
    file.write("    # header.append('NEW_COLUMN')\n")
    file.write("    # for i, j in enumerate(data):\n")
    file.write("    #     data[i].append(NEW_VALUE)\n")
    file.write("    #\n")
    file.write("    # Keep lines that match a criteria\n")
    file.write("    # data_new = []\n")
    file.write("    # for i, j in enumerate(data):\n")
    file.write("    #     line = dict(zip(header, j))\n")
    file.write("    #     if line['CSV_COLUMN'].....\n")
    file.write("    #         data_new.append(j)\n")
    file.write("    # return header, data_new\n")
    file.write("\n")
    file.write(
        f"processor = Processor(src_{model_mapped_name}, schema_overrides={model_mapped_name}_schema, delimiter='{csv_delimiter}, preprocess=preprocess_{model_class_name}')\n\n"
    )
    file.write("\n")


def odoo_type_to_polars_type(odoo_type: str) -> str:
    """Maps Odoo field types to Polars DataType strings."""
    mapping = {
        "char": "pl.Utf8",
        "text": "pl.Utf8",
        "html": "pl.Utf8",
        "selection": "pl.Utf8",
        "monetary": "pl.Float64",
        "float": "pl.Float64",
        "integer": "pl.Int64",
        "boolean": "pl.Boolean",
        "date": "pl.Date",
        "datetime": "pl.Datetime",
        "many2one": "pl.Utf8",
        "many2one_reference": "pl.Int64",
        "many2many": "pl.Utf8",
        "binary": "pl.Utf8",
        "json": "pl.Utf8",
        "one2many": "pl.Utf8",
        "properties": "pl.Utf8",
        "properties_defenition": "pl.Utf8",
        "reference": "pl.Utf8",
    }
    return mapping.get(odoo_type, "pl.Utf8")


def write_end(file: io.TextIOWrapper) -> None:
    """Write the end of the generated python script.

    Args:
        file: The file object to write to.
    """
    ctx = ""
    ctx_opt = []

    if dbname and not offline:
        if has_tracked_fields:
            ctx_opt.append("'tracking_disable': True")
        if has_computed_fields:
            ctx_opt.append("'defer_fields_computation': True")
        if wmetadata:
            ctx_opt.append("'write_metadata': True")

    if ctx_opt:
        ctx = f"'context': {{{', '.join(ctx_opt)}}}, "

    file.write(
        f"processor.process({model_mapping_name}, dest_{model_mapped_name}, {{'config': destination_config_file, 'model': '{model}', {ctx}'groupby': '', 'worker': DEFAULT_WORKER, 'batch_size': DEFAULT_BATCH_SIZE}}, 'set')\n\n"
    )
    file.write(
        f"processor.write_to_file('{model_mapped_name}{script_extension}', python_exe='{default_python_exe}', path='{default_path}')\n\n"
    )


def write_mapping(file: io.TextIOWrapper) -> None:
    """Write the fields mapping and schema of the generated python script.

    Args:
        file: The file object to write to.
    """
    if not dbname or offline:
        file.write(f"{model_mapping_name} = {{\n    'id': None,\n}}\n\n")
        file.write(f"{model_mapped_name}_schema = None\n\n")
        return

    fields = load_fields()

    def field_filter(f: ModelField) -> bool:
        if f.name == "__last_update":
            return False
        if wstored and not f.store:
            return False
        if not wo2m and f.type == "one2many":
            return False
        if not wmetadata and f.name in (
            "create_uid",
            "write_uid",
            "create_date",
            "write_date",
            "active",
        ):
            return False
        return True

    fields = filter(field_filter, fields)
    fields = sorted(
        fields, key=lambda f: ((f.name != "id"), not f.is_required(), f.name)
    )

    if skeleton in ("dict", "map"):
        # --- Write the Schema Dictionary ---
        file.write(f"{model_mapped_name}_schema = {{\n")
        for f in fields:
            polars_type = odoo_type_to_polars_type(f.type)
            file.write(f"    '{f.get_mapping_name()}': {polars_type},\n")
        file.write("}\n\n")

    if skeleton == "dict":
        file.write(f"{model_mapping_name} = {{\n")
        for f in fields:
            if verbose:
                sys.stdout.write(f"Write field {f.name}\n")
            line_start = (
                "# "
                if (required and not f.is_required() and f.name != "id")
                or f.import_warn_msg
                else ""
            )
            file.write(f"    # {f.get_info()}\n")
            mapper_command = f.get_mapper_command().replace(
                "OBJECT_XMLID_PREFIX", f"PREFIX_{model_mapped_name.upper()}"
            )
            file.write(
                f"    {line_start}'{f.get_mapping_name()}': {mapper_command},\n"
            )
        file.write("}\n\n")

    elif skeleton == "map":
        function_prefix = f"handle_{model_mapped_name}_"
        for f in fields:
            if verbose:
                sys.stdout.write(f"Write map function of field {f.name}\n")
            line_start = (
                "# "
                if (required and not f.is_required()) or f.import_warn_msg
                else ""
            )
            mapper_command = f.get_mapper_command().replace(
                "OBJECT_XMLID_PREFIX", f"PREFIX_{model_mapped_name.upper()}"
            )
            file.write(f"{line_start}def {function_prefix}{f.name}(line):\n")
            file.write(f"{line_start}    return {mapper_command}(line)\n\n")

        file.write(f"{model_mapping_name} = {{\n")
        for f in fields:
            if verbose:
                sys.stdout.write(f"Write field {f.name}\n")
            line_start = (
                "# "
                if (required and not f.is_required() and f.name != "id")
                or f.import_warn_msg
                else ""
            )
            file.write(f"    # {f.get_info()}\n")
            file.write(
                f"    {line_start}'{f.get_mapping_name()}': {function_prefix}{f.name},\n"
            )
        file.write("}\n\n")

    # Add selection dictionaries if --map-selection
    if mapsel:
        if verbose:
            sys.stdout.write("Write mapping of selection fields\n")
        with open(Path(base_dir) / "mapping.py", "a", encoding="utf-8") as pf:
            pf.write(f"# Selection fields in model {model}\n\n")
            for f in filter(lambda x: x.type == "selection", fields):
                sys.stdout.write(f"Write mapping of selection field {f.name}\n")
                line_start = "# " if (required and not f.is_required()) else ""
                pf.write(f"{line_start}{model_mapped_name}_{f.name}_map = {{\n")
                for sel in f.selection:
                    key, val = sel.split(selection_sep)
                    pf.write(
                        f'{line_start}    "{val.strip()}": {key.strip()},\n'
                    )
                pf.write(f"{line_start}}}\n\n")


def model_exists(model: str) -> bool:
    """Return True if 'model' is scaffoldable.

    Args:
        model: The model name to check.

    Returns:
        True if the model exists, False otherwise.
    """
    connection = conf_lib.get_connection_from_config(config)
    model_model = connection.get_model("ir.model")
    res = model_model.search_count(
        [("model", "=", model), ("transient", "=", False)]
    )
    return res != 0


def scaffold_model() -> None:
    """Create the python script."""
    global offline
    global dbname
    global host
    import configparser

    cfg = configparser.ConfigParser(
        defaults={"protocol": "xmlrpc", "port": 8069}
    )
    cfg.read(str(config))
    host = cfg.get("Connection", "hostname")
    dbname = cfg.get("Connection", "database")
    login = cfg.get("Connection", "login")
    uid = cfg.get("Connection", "uid")

    sys.stdout.write(
        f"Using connection file: {config} (db: {dbname}, host: {host}, login: {login}, uid: {uid})\n"
    )

    if not dbname:
        offline = True
    elif not model_exists(model):
        sys.stderr.write(f"Model {model} not found\n")
        return

    do_file = skeleton or offline
    outfile_path = Path(outfile)

    if outfile_path.is_file():
        if force:
            if verbose:
                sys.stdout.write(
                    f"Output file {outfile_path} already exists and will be overwritten.\n"
                )
        else:
            sys.stderr.write(f"The file {outfile_path} already exists.\n")
            do_file = False

    if do_file:
        # Write the file
        with outfile_path.open("w", encoding="utf-8") as of:
            write_begin(of)
            write_mapping(of)
            write_end(of)

        if offline:
            sys.stdout.write(
                f"Minimal skeleton code generated in {outfile_path}{' because no database is defined' if not dbname else ''}\n"
            )
        else:
            sys.stdout.write(f"Skeleton code generated in {outfile_path}\n")
    else:
        sys.stdout.write(
            "Skeleton code not generated. Use option -k|--skeleton or -n|--offline or -f|--force to generate the python script.\n"
        )

    dirname = outfile_path.parent

    if append:
        # Add command to transform script
        script = dirname / f"transform{script_extension}"
        if platform.system() == "Windows":
            line = f"echo Transform {model_mapped_name}\npython {model_mapped_name}.py > %LOGDIR%\\transform_{model_mapped_name}_out.log 2> %LOGDIR%\\transform_{model_mapped_name}_err.log\n"
        else:
            os.system(f'sed -i "$ d" {script}')
            line = f"load_script {model_mapped_name}\nchmod +x *.sh\n"
        with script.open("a", encoding="utf-8") as f:
            f.write(line)
        sys.stdout.write(f"Script {model_mapped_name}.py added in {script}\n")

        # Add command to load script
        script = dirname / f"load{script_extension}"
        if platform.system() == "Windows":
            line = f"echo Load {model_mapped_name}\ncall {model_mapped_name}{script_extension} > %LOGDIR%\\load_{model_mapped_name}_out.log 2> %LOGDIR%\\load_{model_mapped_name}_err.log\n"
        else:
            line = f"load_script {model_mapped_name}\n"
        with script.open("a", encoding="utf-8") as f:
            f.write(line)
        sys.stdout.write(
            f"Script {model}{script_extension} added in {script}\n"
        )

        # Add model to prefix.py
        if not wxmlid:
            script = dirname / "prefix.py"
            line = f"PREFIX_{model_mapped_name.upper()} = f'{{project_name}}_{model_mapped_name}'\n"
            with script.open("a", encoding="utf-8") as f:
                f.write(line)
            sys.stdout.write(
                f"Prefix PREFIX_{model_mapped_name.upper()} added in {script}\n"
            )
        else:
            if verbose:
                sys.stdout.write(
                    "XML_ID prefix not added because of option --with-xmlid\n"
                )

        # Add model to files.py
        script = dirname / "files.py"
        with script.open("a", encoding="utf-8") as f:
            f.write(f"# Model {model}\n")
            f.write(
                f"src_{model_mapped_name} = data_src_dir / '{model_mapped_name}.csv'\n"
            )
            f.write(
                f"dest_{model_mapped_name} = data_dest_dir / '{model}.csv'\n"
            )
        sys.stdout.write(f"{model} files added in {script}\n")

        # Add model to clean_data.py
        script = dirname / "clean_data.py"
        with script.open("a", encoding="utf-8") as f:
            f.write(
                "delete_xml_id(connection, '{}', f'{{project_name}}_{}', demo)\n".format(
                    model, model_mapped_name
                )
            )
        sys.stdout.write(f"Model {model} added in {script}\n")
    else:
        sys.stdout.write(
            f"You should probably add this model in files.py, prefix.py, clean_data.py, transform{script_extension} and load{script_extension} with -a|--append\n"
        )


def list_models() -> None:
    """List installed models in the target Odoo instance."""
    connection = conf_lib.get_connection_from_config(config)
    model_model = connection.get_model("ir.model")

    models = model_model.search_read(
        [("transient", "=", False), ("model", "!=", "_unknown")],
        ["model", "name"],
    )

    if not models:
        sys.stdout.write("No model found !")
        return

    for m in sorted(models, key=lambda f: f["model"]):
        sys.stdout.write(f"{m['model']} ({m['name']})\n")


def show_version() -> None:
    """Show the version of the script."""
    sys.stdout.write(f"{module_name} {module_version}\n")


##############################################################################
# MAIN
##############################################################################


def create_export_script_file(
    model: str,
    model_mapped_name: str,
    outfile: Path,
    script_extension: str,
    source_config: str,
) -> None:
    """Create a shell script to export data based on the generated mapper."""
    mapper_file_name = f"{model_mapped_name}.py"
    mapper_file_path = Path(outfile).parent / mapper_file_name

    if not mapper_file_path.is_file():
        sys.stderr.write(
            f"Error: Mapper file {mapper_file_path} not found. Please generate it first using -m MODEL.\n"
        )
        sys.exit(1)

    with mapper_file_path.open("r", encoding="utf-8") as f:
        mapper_content = f.read()

    # Simple parsing to extract field names from the mapping dictionary
    # This assumes the mapping is defined as a dictionary named 'mapping_<model_mapped_name>'
    # and each field is a key in that dictionary.
    field_names = []
    mapping_var_name = f"mapping_{model_mapped_name}"

    # Find the mapping dictionary definition
    mapping_start = mapper_content.find(f"{mapping_var_name} = {{")
    if mapping_start == -1:
        sys.stderr.write(
            f"Error: Could not find mapping dictionary '{mapping_var_name}' in {mapper_file_path}.\n"
        )
        sys.exit(1)

    mapping_end = mapper_content.find("}\n\n", mapping_start)
    if mapping_end == -1:
        # Fallback for dictionaries that might end differently
        mapping_end = mapper_content.find("\n}", mapping_start)
        if mapping_end != -1:
            mapping_end += 2  # include the closing brace
        else:
            sys.stderr.write(
                f"Error: Could not find end of mapping dictionary in {mapper_file_path}.\n"
            )
            sys.exit(1)

    mapping_dict_str = mapper_content[
        mapping_start + len(f"{mapping_var_name} = {{") : mapping_end
    ]

    # Use a regular expression to reliably extract field names (dictionary keys)
    # This pattern looks for a quoted string (the key) followed by a colon.
    key_pattern = re.compile(r"^\s*['\"]([^'\"]+)['\"]\s*:")

    for line in mapping_dict_str.splitlines():
        line = line.strip()
        if line.startswith("#") or not line:
            continue

        match = key_pattern.match(line)
        if match:
            field_name = match.group(1)
            field_names.append(field_name)

    if not field_names:
        sys.stderr.write(
            f"Warning: No field names found in mapper file {mapper_file_path}.\n"
        )

    export_script_name = f"{model_mapped_name}_export{script_extension}"
    export_script_path = Path(outfile).parent / export_script_name

    with export_script_path.open("w", encoding="utf-8") as f:
        if platform.system() != "Windows":
            f.write("#!/usr/bin/env bash\n\n")
        f.write("odoo-data-flow export \\\n")
        f.write(f'    --config "{source_config}" \\\n')
        f.write(f'    --model "{model}" \\\n')
        f.write(f'    --output "origin/{model_mapped_name}.csv" \\\n')
        f.write(f'    --fields "{",".join(field_names)}" \\\n')
        f.write("    --technical-names\n")

    if platform.system() != "Windows":
        export_script_path.chmod(0o755)

    sys.stdout.write(f"Export script created at {export_script_path}\n")


def main() -> None:
    """Main function."""
    global \
        module_name, \
        conf_dir_name, \
        orig_dir_name, \
        data_dir_name, \
        log_dir_name, \
        selection_sep, \
        default_base_dir
    global \
        scaffold, \
        base_dir, \
        dbname, \
        host, \
        model, \
        userid, \
        config, \
        outfile, \
        required, \
        skeleton, \
        wstored, \
        wo2m, \
        wmetadata, \
        mapsel, \
        wxmlid, \
        maxdescr, \
        offline, \
        append, \
        list, \
        force, \
        verbose, \
        version, \
        fieldname
    global \
        script_extension, \
        project_name, \
        model_mapped_name, \
        model_class_name, \
        model_mapping_name, \
        csv_delimiter, \
        default_python_exe, \
        default_path
    global conf_dir, orig_dir, orig_raw_dir, data_dir, log_dir

    module_name = Path(sys.argv[0]).name
    conf_dir_name = "conf"
    orig_dir_name = "origin"
    data_dir_name = "data"
    log_dir_name = "log"
    selection_sep = ": "
    default_base_dir = Path(".")

    script_extension = ".cmd" if platform.system() == "Windows" else ".sh"

    module_descr = f"""Version: {module_version}
    Create the structure of an import project and model skeleton codes working
    with odoo_data_flow (https://github.com/OdooDataFlow/odoo-data-flow).

    Functionalities:
    ----------------
    - Create the project structure:
    {module_name} -s -p PATH [-d DBNAME] [-t HOST] [-u USERID] [-f] [-v]

    - Skeleton a model:
    {module_name} -m MODEL [-a] [--map-selection] [--with-xmlid] [-r] [-k map | -n]
                     [--with-one2many] [--with-metadata] [--stored] [-v]
                     [--max-descr MAXDESCR] [-f] [-o OUTFILE] [-c CONFIG]

    - Show available models:
    {module_name} -l [-c CONFIG]
    """

    module_epilog = """
    More information on https://github.com/OdooDataFlow/odoo_dataflow_scaffold
    """

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=f"Version: {module_version}\nTool for scaffolding odoo-data-flow projects.",
    )
    parser.add_argument(
        "-s",
        "--scaffold",
        dest="scaffold",
        action="store_true",
        help="create the folders structure and the basic project files",
    )
    parser.add_argument(
        "-p",
        "--path",
        dest="path",
        type=Path,
        default=default_base_dir,
        required=False,
        help="project path (default: current dir)",
    )
    parser.add_argument(
        "-d",
        "--db",
        dest="dbname",
        default="",
        required=False,
        help="target database. If omitted, it is the first part of HOST",
    )
    parser.add_argument(
        "-t",
        "--host",
        dest="host",
        default="localhost",
        required=False,
        help="hostname of the database (default: localhost)",
    )
    parser.add_argument(
        "-u",
        "--userid",
        dest="userid",
        type=int,
        default=2,
        required=False,
        help="user id of RPC calls (default: 2)",
    )
    parser.add_argument(
        "-m",
        "--model",
        dest="model",
        required=False,
        help="technical name of the model to skeleton (ex: res.partner)",
    )
    parser.add_argument(
        "-c",
        "--config",
        dest="config",
        type=Path,
        default=Path(conf_dir_name) / "connection.conf",
        help="Default config file if source/destination are not set.",
    )
    parser.add_argument(
        "--source-config",
        dest="source_config",
        type=Path,
        help="Source Odoo instance for reading metadata.",
    )
    parser.add_argument(
        "--destination-config",
        dest="destination_config",
        type=Path,
        help="Destination Odoo instance for writing import scripts.",
    )
    parser.add_argument(
        "-o",
        "--outfile",
        dest="outfile",
        type=Path,
        required=False,
        help="python script of the model skeleton code (default: model name with dots replaced by underscores)",
    )
    parser.add_argument(
        "-k",
        "--skeleton",
        dest="skeleton",
        choices=["dict", "map"],
        default="dict",
        required=False,
        help="skeleton code type. dict: generate mapping as a simple dictionary. map: create the same dictionary with map functions for each field (default: dict)",
    )
    parser.add_argument(
        "-r",
        "--required",
        dest="required",
        action="store_true",
        help="keep only the required fields without default value (comment the optional fields",
    )
    parser.add_argument(
        "--field-name",
        dest="fieldname",
        choices=["tech", "user"],
        default="user",
        required=False,
        help="Field name in import file. tech=technical name, user=User name (default: user). Generates the mapping accordingly.",
    )
    parser.add_argument(
        "--stored",
        dest="wstored",
        action="store_true",
        help="include only stored fields",
    )
    parser.add_argument(
        "--with-o2m",
        dest="wo2m",
        action="store_true",
        help="include one2many fields",
    )
    parser.add_argument(
        "--with-metadata",
        dest="wmetadata",
        action="store_true",
        help="include metadata fields",
    )
    parser.add_argument(
        "--map-selection",
        dest="mapsel",
        action="store_true",
        help="generate inverse mapping dictionaries (visible value -> technical value) of selection fields in mapping.py",
    )
    parser.add_argument(
        "--with-xmlid",
        dest="wxmlid",
        action="store_true",
        help="assume the client file contains XML_IDs in identifier fields",
    )
    parser.add_argument(
        "--max-descr",
        dest="maxdescr",
        type=int,
        default=10,
        help="limit long descriptions of default value and compute method to MAXDESCR lines (default: 10)",
    )
    parser.add_argument(
        "-n",
        "--offline",
        dest="offline",
        action="store_true",
        help="don't fetch fields from model. Create a minimal skeleton",
    )
    parser.add_argument(
        "-a",
        "--append",
        dest="append",
        action="store_true",
        help="add model references to files.py, prefix.py and action scripts",
    )
    parser.add_argument(
        "-f",
        "--force",
        dest="force",
        action="store_true",
        help="overwrite files and directories if existing.",
    )
    parser.add_argument(
        "--create-export-script",
        dest="create_export_script",
        action="store_true",
        help="Create a shell script to export data based on the generated mapper.",
    )
    parser.add_argument(
        "--export-fields",
        dest="export_fields",
        action="store_true",
        help="Output a comma-separated list of field names suitable for export.",
    )
    parser.add_argument(
        "-l",
        "--list",
        dest="list",
        action="store_true",
        help="List installed models in the target Odoo instance",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="store_true",
        help="display process information",
    )
    parser.add_argument(
        "--version", dest="version", action="store_true", help="show version"
    )

    args = parser.parse_args()

    # Manage params
    scaffold = args.scaffold
    base_dir = args.path
    dbname = args.dbname
    host = args.host
    model = args.model
    userid = args.userid
    config = args.config
    outfile = args.outfile
    required = args.required
    skeleton = args.skeleton
    wstored = args.wstored
    wo2m = args.wo2m
    wmetadata = args.wmetadata
    mapsel = args.mapsel
    wxmlid = args.wxmlid
    maxdescr = args.maxdescr
    offline = args.offline
    append = args.append
    list_models_flag = args.list
    force = args.force
    verbose = args.verbose
    version = args.version
    fieldname = args.fieldname
    create_export_script = args.create_export_script
    export_fields = args.export_fields

    # --- Start of Corrected Logic ---

    # Determine which config files to use
    source_config_name = args.source_config or args.config or "connection.conf"
    dest_config_name = (
        args.destination_config or args.config or "dest_connection.conf"
    )

    # Read config file early to get database name if not provided by CLI
    # Read dbname from source config for operations that need it
    config_path = args.path / source_config_name
    dbname = args.dbname
    if not dbname:
        config_path = base_dir / source_config_name
        print(f"Reading database name from config file {config_path} ...")
        if config_path.is_file():
            cfg = configparser.ConfigParser()
            cfg.read(str(config_path))
            if cfg.has_section("Connection"):
                dbname = cfg.get("Connection", "database")
                print(f"Found database name *{dbname}* from config file.")

    # 2. Now perform actions that require the database name
    if version:
        show_version()
        sys.exit(0)
    if list_models_flag:
        list_models()
        sys.exit(0)

    if model:
        model_mapped_name = model.replace(".", "_")
        if not outfile:
            outfile = Path(f"{model_mapped_name}.py")

    if create_export_script:
        if not model:
            sys.stderr.write(
                "Error: --create-export-script requires -m MODEL to be specified.\n"
            )
            sys.exit(1)
        create_export_script_file(
            model,
            model_mapped_name,
            outfile,
            script_extension,
            source_config_name,
        )
        sys.exit(0)

    if export_fields:
        print("export fields called")
        if not model:
            sys.stderr.write(
                "Error: --export-fields requires -m MODEL to be specified.\n"
            )
            sys.exit(1)
        if not dbname:
            sys.stderr.write(
                "Error: --export-fields requires a database connection. Please provide -d DBNAME or ensure connection.conf is properly configured.\n"
            )
            sys.exit(1)

        sys.stdout.write("Printing import-compatible fields to console...\n")
        fields = load_fields()
        exportable_field_names = []
        for f in fields:
            # Exclude fields not suitable for direct import
            if f.name in ("create_uid", "write_uid"):
                continue
            if f.name in (
                "image_small",
                "image_medium",
                "image_128",
                "image_256",
                "image_512",
                "image_1024",
            ):
                continue
            if f.compute:
                continue
            if f.related:
                continue
            if not f.store:
                continue
            if f.type == "one2many":
                continue

            exportable_field_names.append(f.name)

    # If no action set, prompt for scaffolding
    action_args = [scaffold, model]
    if not any(action_args):
        response = input(
            f"Do you want the create the folder structure in {base_dir} ? (y|N): "
        )
        scaffold = "Y" == response.upper()

    # If still no action, exit with help message
    if not scaffold and not model:
        sys.stderr.write(
            "You need to set an action with -s|--scaffold or -m|--model or -l|--list\n"
        )
        sys.stderr.write(f"Type {module_name} -h|--help for help\n")
        sys.exit(1)

    # Do cascaded actions
    script_extension = ".cmd" if platform.system() == "Windows" else ".sh"

    if args.scaffold:
        scaffold_dir(args, source_config_name, dest_config_name)

        if is_remote_host(host) and not dbname:
            dbname = host.split(".")[0]
            sys.stdout.write(f"Database is set by default to {dbname}.\n")

        scaffold_dir(args, str(source_config_name), str(dest_config_name))

    if model:
        model_mapped_name = model.replace(".", "_")
        model_class_name = model.title().replace(".", "")
        model_mapping_name = f"mapping_{model_mapped_name}"
        if not outfile:
            outfile = Path(f"{model_mapped_name}.py")
        config = base_dir / config
        csv_delimiter = ";"
        default_python_exe = ""
        default_path = ""

        scaffold_model()


if __name__ == "__main__":
    main()
