"""
Created on Tue Mar  3 14:08:04 2020

@author: hoeren
"""
import os
import pickle
import platform
import sqlite3

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QObject

from ATE.spyder.widgets.constants import TableIds as TableId
from ATE.spyder.widgets.database import ORM
from ATE.spyder.widgets.database.Device import Device
from ATE.spyder.widgets.database.Die import Die
from ATE.spyder.widgets.database.Hardware import Hardware
from ATE.spyder.widgets.database.Maskset import Maskset
from ATE.spyder.widgets.database.Package import Package
from ATE.spyder.widgets.database.Product import Product
from ATE.spyder.widgets.database.Program import Program
from ATE.spyder.widgets.database.QualificationFlow import QualificationFlowDatum
from ATE.spyder.widgets.database.Sequence import Sequence
from ATE.spyder.widgets.database.Test import Test
from ATE.spyder.widgets.database.TestTarget import TestTarget
from ATE.spyder.widgets.validation import is_ATE_project


tables = {'hardwares': Hardware,
          'masksets': Maskset,
          'dies': Die,
          'packages': Package,
          'devices': Device,
          'products': Product,
          'tests': Test,
          'testtargets': TestTarget}


class ProjectNavigation(QObject):
    '''
    This class takes care of the project creation/navigation/evolution.
    '''
    # The parameter contains the type of the dbchange (i.e. which table was altered)
    verbose = True

    def __init__(self, project_directory, parent, project_quality=''):
        super().__init__()
        self.parent = parent
        # self.workspace_path = workspace_path
        self.__call__(project_directory, project_quality)

    def __call__(self, project_directory, project_quality=''):
        # determine OS, determine user & desktop
        self.os = platform.system()
        if self.os == 'Windows':
            self.desktop_path = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
        elif self.os == 'Linux':
            self.desktop_path = os.path.join(os.path.join(os.path.expanduser('~')), 'Desktop')
        elif self.os == 'Darwin':  # TODO: check on mac if this works
            self.desktop_path = os.path.join(os.path.join(os.path.expanduser('~')), 'Desktop')
        else:
            raise Exception("unrecognized operating system")
        self.user = self.desktop_path.split(os.sep)[-2]
        self.template_directory = os.path.join(os.path.dirname(__file__), 'templates')

        # TODO: take the keychain in here ?!?

        if project_directory == '':
            self.project_directory = ''
            self.active_target = ''
            self.active_hardware = ''
            self.active_base = ''
            self.project_name = ''
            self.project_quality = ''
            self.db_file = ''
            self.con = None
        else:
            self.project_directory = project_directory
            self.active_target = ''
            self.active_hardware = ''
            self.active_base = ''
            self.project_name = os.path.basename(self.project_directory)

            self.db_file = os.path.join(project_directory, f"{self.project_name}.sqlite3")

            project_quality_file = os.path.join(self.project_directory, 'project_quality.pickle')

            if not os.path.exists(self.db_file):  # brand new project, initialize it.
                self.create_project_structure()
                self.project_quality = project_quality
                if project_quality != '':
                    with open(project_quality_file, 'wb') as writer:
                        pickle.dump(project_quality, writer, 4)
            else:
                if os.path.exists(project_quality_file):
                    with open(project_quality_file, 'rb') as reader:
                        self.project_quality = pickle.load(reader)
                else:
                    self.project_quality = ''

                self._set_folder_structure()

            self.orm = ORM.ORM(self.db_file)
            self.orm.init_database()

            self.con = sqlite3.connect(self.db_file)
            self.cur = self.con.cursor()

        if self.verbose:
            print("Navigator:")
            print(f"  - operating system = '{self.os}'")
            print(f"  - user = '{self.user}'")
            print(f"  - desktop path = '{self.desktop_path}'")
            print(f"  - template path = '{self.template_directory}'")
            print(f"  - project path = '{self.project_directory}'")
            print(f"  - active target = '{self.active_target}'")
            print(f"  - active hardware = '{self.active_hardware}'")
            print(f"  - active base = '{self.active_base}'")
            print(f"  - project name = '{self.project_name}'")
            print(f"  - project grade = '{self.project_quality}'")
            print(f"  - project db file = '{self.db_file}'")

    def update_toolbar_elements(self, active_hardware, active_base, active_target):
        self.active_hardware = active_hardware
        self.active_base = active_base
        self.active_target = active_target
        self._store_settings()
        self.parent.toolbar_changed.emit(self.active_hardware, self.active_base, self.active_target)

    def update_active_hardware(self, hardware):
        self.active_hardware = hardware
        self.parent.hardware_activated.emit(hardware)

    def _set_folder_structure(self):
        # make sure that the doc structure is obtained
        doc_path = os.path.join(self.project_directory, "doc")
        os.makedirs(os.path.join(doc_path, "audits"), exist_ok=True)
        os.makedirs(os.path.join(doc_path, "exports"), exist_ok=True)

    def create_project_structure(self):
        '''
        this method creates a new project `self.project_directroy` *MUST* exist
        '''
        from ATE.spyder.widgets.coding.generators import project_generator
        project_generator(self.project_directory)

    def add_project(self, project_name, project_quality=''):
        project_directory = os.path.join(self.workspace_path, project_name)
        self.__call__(project_directory, project_quality)

    # def dict_projects(self, workspace_path=''):
    #     '''
    #     given a workspace_path, create a list with projects as key, and their
    #     (absolute) project_path as value.
    #     if workspace_path is empty, the parent's "workspace_path" is used.
    #     '''
    #     retval = {}
    #     if workspace_path == '':
    #         workspace_path = self.workspace_path
    #     for directory in os.listdir(workspace_path):
    #         full_directory = os.path.join(workspace_path, directory)
    #         if os.path.isdir(full_directory):
    #             retval[directory] = full_directory
    #     return retval

    # def list_projects(self, workspace_path=''):
    #     '''
    #     given a workspace_path, extract a list of all projects
    #     '''
    #     if workspace_path == '':
    #         workspace_path = self.workspace_path
    #     return list(self.dict_projects(workspace_path))

    # def list_ATE_projects(self, workspace_path=''):
    #     '''
    #     given a workspace_path, extract a list of all ATE projects
    #     if workspace_path is empty, the parent's "workspace_path" will be used.
    #     '''
    #     if workspace_path == '':
    #         workspace_path = self.workspace_path
    #     return list(self.dict_ATE_projects(workspace_path))

    # def dict_ATE_projects(self, workspace_path=''):
    #     '''
    #     given a workspace_path, create a dictionary with all ATE projects as key,
    #     and the (absolute) project_path as value.
    #     if workspace_path is empty, the parent's "workspace_path" is used.
    #     '''
    #     retval = {}
    #     if workspace_path == '':
    #         workspace_path = self.workspace_path
    #     all_projects = self.dict_projects(workspace_path)
    #     for candidate in all_projects:
    #         possible_ATE_project = all_projects[candidate]
    #         if is_ATE_project(possible_ATE_project):
    #             retval[candidate] = possible_ATE_project
    #     return retval

    def add_hardware(self, definition, is_enabled=True):
        '''This method adds a hardware setup to the project.

        The hardware is defined in the 'definition' parameter as follows:
            hardware_definition = {
                'hardware': 'HW0',
                'PCB': {},
                'tester': ('SCT', 'import stuff'),
                'instruments': {},
                'actuators': {}}

        This method returns the name of the Hardware on success and raises an
        exception on fail (no sense of continuing, this should work!)
        '''
        awaited_name = self.get_next_hardware()
        new_hardware = definition['hardware']
        # TODO: fix me!!!!!!!!!!!!!!!
        # if not awaited_name == new_hardware:
        #     raise Exception(f"something wrong with the name !!! '{awaited_name}'<->'{new_hardware}'")

        try:  # make the directory structure
            from ATE.spyder.widgets.coding.generators import hardware_generator
            hardware_generator(self.project_directory, definition)
        except Exception as e:  # explode on fail
            print(f"failed to create hardware structure for {definition['hardware']}")
            raise e

        # blob do not have to contain hardware name it's already our primary key
        # TODO: cleaner impl.
        definition.pop('hardware')
        # fill the database on success
        Hardware.add(self.get_session(), new_hardware, definition, is_enabled)

        # let ATE.spyder.widgets know that we have new hardware
        self.parent.hardware_added.emit(new_hardware)
        self.parent.database_changed.emit(TableId.Hardware())

    def update_hardware(self, hardware, definition):
        '''
        this method will update hardware 'name' with 'definition'
        if name doesn't exist, a KeyError will be thrown
        '''
        # TODO: cleaner impl.
        # blob do not have to contain hardware name it's already our primary key
        definition.pop('hardware')
        Hardware.update(self.get_session(), hardware, definition)

    def get_session(self):
        return self.orm.session()

    def get_hardwares_info(self):
        '''
        This method will return a DICTIONARY with as key all hardware names,
        and as key the definition.
        '''
        return self.get_session().query(Hardware)

    def get_active_hardware_names(self):
        return [hw.name for hw in Hardware.get_all(self.get_session()) if hw.is_enabled]

    def get_hardware_names(self):
        '''
        This method will return a list of all hardware names available
        '''
        return [hardware.name for hardware in Hardware.get_all(self.get_session())]

    def get_next_hardware(self):
        '''
        This method will determine the next available hardware name
        '''
        latest_hardware = self.get_latest_hardware()
        if latest_hardware == '':
            return "HW0"
        else:
            latest_hardware_number = int(latest_hardware.replace('HW', ''))
            return f"HW{latest_hardware_number + 1}"

    def get_latest_hardware(self):
        '''
        This method will determine the latest hardware name and return it
        '''
        available_hardwares = self.get_hardware_names()
        if len(available_hardwares) == 0:
            return ""
        else:
            return available_hardwares[-1]

    def get_hardware_definition(self, name):
        '''
        this method retreives the hwr_data for hwr_nr.
        if hwr_nr doesn't exist, an empty dictionary is returned
        '''
        return Hardware.get_definition(self.get_session(), name)

    def remove_hardware(self, name):
        Hardware.remove(self.get_session(), name)
        self.parent.database_changed.emit(TableId.Hardware())

    def add_maskset(self, name, customer, definition, is_enabled=True):
        '''
        this method will insert maskset 'name' and 'definition' in the
        database, but prior it will check if 'name' already exists, if so
        it will trow a KeyError
        '''
        Maskset.add(self.get_session(), name, customer, definition, is_enabled)
        self.parent.database_changed.emit(TableId.Maskset())

    def update_maskset(self, name, definition):
        '''
        this method will update the definition of maskset 'name' to 'definition'
        '''
        Maskset.update(self.get_session(), name, '', definition)

    def get_masksets(self):
        '''
        this method returns a DICTIONARY with as key all maskset names,
        and as value the tuple (customer, definition)
        '''
        return Maskset.get_all(self.get_session())

    def get_available_maskset_names(self):
        '''
        this method returns a DICTIONARY with as key all maskset names,
        and as value the tuple (customer, definition)
        '''
        return self.get_masksets()

    def get_maskset_names(self):
        '''
        this method lists all available masksets
        '''
        return list(self.get_masksets())

    def get_ASIC_masksets(self):
        '''
        this method lists all 'ASIC' masksets
        '''
        return Maskset.get_ASIC_masksets(self.get_session())

    def get_ASSP_masksets(self):
        '''
        this method lists all 'ASSP' masksets
        '''
        return Maskset.get_ASSP_masksets(self.get_session())

    def get_maskset_definition(self, name):
        '''
        this method will return the definition of maskset 'name'
        '''
        return Maskset.get_definition(self.get_session(), name)

    def get_maskset_customer(self, name):
        '''
        this method will return the customer of maskset 'name'
        (empty string means no customer, thus 'ASSP')
        '''
        return Maskset.get(self.get_session(), name).customer

    def remove_maskset(self, name):
        Maskset.remove(self.get_session(), name)
        self.parent.database_changed.emit(TableId.Maskset())

    def add_die(self, name, hardware, maskset, quality, grade, grade_reference, type, customer, is_enabled=True):
        '''
        this method will add die 'name' with the given attributes to the database.
        if 'maskset' or 'hardware' doesn't exist, a KeyError will be raised.
        Also if 'name' already exists, a KeyError will be raised.
        if grade is not 'A'..'I' (9 possibilities) then a ValueError is raised
        if grade is 'A' then grade_reference must be an empty string
        if grade is not 'A', then grade_reference can not be an empty string,
        and it must reference another (existing) die with grade 'A'!
        '''
        Die.add(self.get_session(), name, hardware, maskset, quality, grade, grade_reference, type, customer, is_enabled)

        self.parent.database_changed.emit(TableId.Die())

    def update_die(self, name, hardware, maskset, grade, grade_reference, quality, type, customer, is_enabled=True):
        '''
        this method updates both maskset and hardware for die with 'name'
        '''
        Die.update(self.get_session(), name, hardware, maskset, quality, grade, grade_reference, type, customer)

    def get_dies(self):
        '''
        this method will return a DICTIONARY with as keys all existing die names,
        and as value the tuple (hardware, maskset, grade, grade_reference, customer)
        '''
        return Die.get_all(self.get_session())

    def get_active_die_names(self):
        return [die.name for die in self.get_dies() if die.is_enabled]

    def get_die_names(self):
        '''
        this method will return a LIST of all dies
        '''
        return [die.name for die in self.get_dies()]

    def get_active_die_names_for_hardware(self, hardware):
        '''
        this method will return a LIST of all dies that conform to 'hardware'
        '''
        return [die.name for die in self.get_dies() if die.hardware == hardware and Die.is_enabled]

    def get_die(self, name):
        '''
        this method returns a tuple (hardware, maskset, grade, grade_reference, customer) for die 'name'
        if name doesn't exist, a KeyError will be raised.
        '''
        return Die.get_die(self.get_session(), name)

    def get_die_maskset(self, name):
        '''
        this method returns the maskset of die 'name'
        '''
        return self.get_die(name).maskset

    def get_die_hardware(self, name):
        '''
        this method returns the hardware of die 'name'
        '''
        return self.get_die(name).hardware

    def remove_die(self, name):
        Die.remove(self.get_session(), name)
        self.parent.database_changed.emit(TableId.Die())

# Packages

    def add_package(self, name, leads, is_naked_die, is_enabled=True):
        '''
        this method will insert package 'name' and 'pleads' in the
        database, but prior it will check if 'name' already exists, if so
        it will trow a KeyError
        '''
        Package.add(self.get_session(), name, leads, is_naked_die, is_enabled)

        self.parent.database_changed.emit(TableId.Package())

    def update_package(self, name, leads, is_naked_die, is_enabled=True):
        Package.update(self.get_session(), name, leads, is_naked_die, is_enabled)

    def does_package_name_exist(self, name):
        return self.get_package(name) is not None

    def get_package(self, name):
        return Package.get(self.get_session(), name)

    def is_package_a_naked_die(self, package):
        return self.get_package(package).is_naked_die

    def get_packages_info(self):
        '''
        this method will return a DICTIONARY with ALL packages as key and
        the number of leads as value
        '''
        return Package.get_all(self.get_session())

    def get_available_packages(self):
        '''
        this method will return a DICTIONARY with ALL packages as key and
        the number of leads as value
        '''
        return [package.name for package in self.get_packages_info()]

    def get_packages(self):
        '''
        this method will return a LIST with all packages
        '''
        return list(self.get_packages_info())

# Devices
    def add_device(self, name, hardware, package, definition, is_enabled=True):
        '''
        this method will add device 'name' with 'package' and 'definition'
        to the database.
        if 'name' already exists, a KeyError is raised
        if 'package' doesn't exist, a KeyError is raised
        '''
        Device.add(self.get_session(), name, hardware, package, definition, is_enabled)
        self.parent.database_changed.emit(TableId.Device())

    def update_device(self, name, hardware, package, definition):
        Device.update(self.get_session(), name, hardware, package, definition)

    def get_device_names(self):
        '''
        this method lists all available devices
        '''
        return [device.name for device in Device.get_all(self.get_session())]

    def get_active_device_names_for_hardware(self, hardware_name):
        '''
        this method will return a list of devices for 'hardware_name'
        '''
        return [device.name for device in Device.get_all(self.get_session()) if device.hardware == hardware_name and device.is_enabled]

    def get_devices_for_hardwares(self):
        return [device.name for device in Device.get_all(self.get_session())]

    def get_device_hardware(self, name):
        return Device.get(self.get_session(), name).hardware

    def get_device_package(self, name):
        '''
        this method will return the package of device 'name'
        '''
        return Device.get(self.get_session(), name).package

    def get_device_definition(self, name):
        '''
        this method will return the definition of device 'name'
        '''
        return Device.get_definition(self.get_session(), name)

    def get_device(self, name):
        return {'hardware': self.get_device_hardware(name),
                'package': self.get_device_package(name),
                'definition': self.get_device_definition(name)}

    def get_device_dies(self, device):
        definition = self.get_device_definition(device)
        return definition['dies_in_package']

    def remove_device(self, name):
        Device.remove(self.get_session(), name)
        self.parent.database_changed.emit(TableId.Device())

    def add_product(self, name, device, hardware, quality, grade, grade_reference, type, customer, is_enabled=True):
        '''
        this method will insert product 'name' from 'device' and for 'hardware'
        in the the database, but before it will check if 'name' already exists, if so
        it will trow a KeyError
        '''
        session = self.get_session()
        Product.add(session, name, device, hardware, quality, grade, grade_reference, type, customer, is_enabled)
        self.parent.database_changed.emit(TableId.Product())

    def update_product(self, name, device, hardware, quality, grade, grade_reference, type, customer):
        Product.update(self.get_session(), name, device, hardware, quality, grade, grade_reference, type, customer)

    def get_products_info(self):
        return Product.get_all(self.get_session())

    def get_products(self):
        '''
        this method will return a list of all products
        '''
        return [product.name for product in self.get_products_info()]

    def get_product(self, name):
        return Product.get(self.get_session(), name)

    def get_product_device(self, name):
        return Product.get(self.get_session(), name).device

    def get_products_for_device(self, device_name):
        return [product.name for product in Product.get_for_device(self.get_session(), device_name)]

    def get_product_hardware(self, name):
        return Product.get(self.get_session(), name).hardware

    def remove_product(self, name):
        Product.remove(self.get_session(), name)
        self.parent.database_changed.emit(TableId.Product())

    def tests_get_standard_tests(self, hardware, base):
        '''
        given 'hardware' and 'base', this method will return a LIST
        of all existing STANDARD TESTS.
        '''
        return Test.get_all(self.get_session(), hardware, base, 'standard')

    def add_standard_test(self, name, hardware, base):
        import runpy
        from ATE.spyder.widgets.coding.standard_tests import names as standard_test_names

        if name in standard_test_names:
            temp = runpy.run_path(standard_test_names[name])
            # TODO: fix this
            if not temp['dialog'](name, hardware, base):
                print(f"... no joy creating standard test '{name}'")
        else:
            raise Exception(f"{name} not a standard test ... WTF!")

    def add_custom_test(self, definition, is_enabled=True):
        '''This method adds a 'custom' test to the project.

        'definition' is a structure as follows:

            test_definition = {
                'name': 'trial',
                'type': 'custom', <-- needs to be 'custom' otherwhise explode
                'quality': 'automotive',
                'hardware': 'HW0',
                'base': 'FT',
                'doc_string': ['line1', 'line2'],
                'input_parameters': {
                    'Temperature':    {'Shmoo': True, 'Min': -40.0, 'Default': 25.0, 'Max': 170.0, '10ᵡ': '', 'Unit': '°C', 'fmt': '.0f'},
                    'new_parameter1': {'Shmoo': False, 'Min': -np.inf, 'Default': 0.0, 'Max': np.inf, '10ᵡ': 'μ', 'Unit':  'V', 'fmt': '.3f'},
                    'new_parameter2': {'Shmoo': False, 'Min': -np.inf, 'Default':  0.123456789, 'Max': np.inf, '10ᵡ':  '', 'Unit':  'dB', 'fmt': '.6f'}},
                'output_parameters' : {
                    'new_parameter1': {'LSL': -np.inf, 'LTL':  np.nan, 'Nom':  0.0, 'UTL': np.nan, 'USL': np.inf, '10ᵡ': '', 'Unit': '?', 'fmt': '.3f'},
                    'new_parameter2': {'LSL': -np.inf, 'LTL': -5000.0, 'Nom': 10.0, 'UTL':   15.0, 'USL': np.inf, '10ᵡ': '', 'Unit': '?', 'fmt': '.1f'},
                    'new_parameter3': {'LSL': -np.inf, 'LTL':  np.nan, 'Nom':  0.0, 'UTL': np.nan, 'USL': np.inf, '10ᵡ': '', 'Unit': '?', 'fmt': '.6f'},
                    'new_parameter4': {'LSL': -np.inf, 'LTL':  np.nan, 'Nom':  0.0, 'UTL': np.nan, 'USL': np.inf, '10ᵡ': '', 'Unit': '?', 'fmt': '.3f'}},
                'dependencies' : {}}
        '''

        name = definition['name']
        hardware = definition['hardware']
        base = definition['base']
        test_type = definition['type']

        if test_type != 'custom':
            raise Exception(f"not a 'custom' test!!!")

        # TODO: move this check to the wizard
        tests = self.get_tests_from_db(hardware, base)
        if name in tests:
            # use print as a hint until we fix this
            print('test exists already')
            return

        try:  # generate the test with everythin around it.
            from ATE.spyder.widgets.coding.generators import test_generator
            test_generator(self.project_directory, definition)
        except Exception as e:  # explode on fail
            print(f"failed to create test structure for {definition['hardware']}/{definition['base']}/{definition['name']}")
            raise e

        # add to database on pass
        # TODO: hack is used, this must be refactored
        definition.pop('name')
        definition.pop('hardware')
        definition.pop('base')
        definition.pop('type')
        Test.add(self.get_session(), name, hardware, base, test_type, definition, is_enabled)

        self.parent.database_changed.emit(TableId.NewTest())

    def update_custom_test(self, name, hardware, base, type, definition, is_enabled=True):
        Test.update(self.get_session(), name, hardware, base, type, definition, is_enabled)
        self.parent.database_changed.emit(TableId.Test())

    def get_tests_from_files(self, hardware, base, test_type='all'):
        '''
        given hardware , base and type this method will return a dictionary
        of tests, and as value the absolute path to the tests.
        by searching the directory structure.
        type can be:
            'standard' --> standard tests
            'custom' --> custom tests
            'all' --> standard + custom tests
        '''
        retval = {}
        tests_directory = os.path.join(self.project_directory, 'src', 'tests', hardware, base)
        potential_tests = os.listdir(tests_directory)
        from ATE.spyder.widgets.actions_on.tests import standard_test_names

        for potential_test in potential_tests:
            if potential_test.upper().endswith('.PY'):  # ends with .PY, .py, .Py or .pY
                if '_' not in potential_test.upper().replace('.PY', ''):  # name doesn't contain an underscore
                    if '.' not in potential_test.upper().replace('.PY', ''):  # name doesn't contain extra dot(s)
                        if test_type == 'all':
                            retval[potential_test.split('.')[0]] = os.path.join(tests_directory, potential_test)
                        elif test_type == 'standard':
                            if '.'.join(potential_test.split('.')[0:-1]) in standard_test_names:
                                retval[potential_test.split('.')[0]] = os.path.join(tests_directory, potential_test)
                        elif test_type == 'custom':
                            if '.'.join(potential_test.split('.')[0:-1]) not in standard_test_names:
                                retval[potential_test.split('.')[0]] = os.path.join(tests_directory, potential_test)
                        else:
                            raise Exception('unknown test type !!!')
        return retval

    def get_test_table_content(self, name, hardware, base):
        table = Test.get(self.get_session(), name, hardware, base)
        infos = {'name': table.name, 'hardware': table.hardware, 'type': table.type, 'base': table.base}
        infos.update(table.get_definition())

        return infos

    def get_test_temp_limits(self, test, hardware, base):
        test = self.get_test_table_content(test, hardware, base)
        temp = test['input_parameters']['Temperature']
        return int(temp['Min']), int(temp['Max'])

    def get_tests_from_db(self, hardware, base, test_type='all'):
        '''
        given hardware and base, this method will return a dictionary
        of tests, and as value the absolute path to the tests.
        by querying the database.
        type can be:
            'standard' --> standard tests
            'custom' --> custom tests
            'all' --> standard + custom tests
        '''

        if test_type not in ('standard', 'custom', 'all'):
            raise Exception('unknown test type !!!')

        return Test.get_all(self.get_session(), hardware, base, test_type)

    def remove_test(self, name):
        Test.remove(self.get_session(), name)

        Sequence.remove_test_from_sequence(self.get_session(), name)
        self.parent.database_changed.emit(TableId.Test())

    # ToDo Seems to be unused!
    def delete_test_from_program(self, test_name):
        Sequence.remove_test_from_sequence(self.get_session(), test_name)
        self.parent.database_changed.emit(TableId.Test())

    def get_data_for_qualification_flow(self, quali_flow_type, product):
        return QualificationFlowDatum.get_data_for_flow(self.get_session(), quali_flow_type, product)

    def get_unique_data_for_qualifcation_flow(self, quali_flow_type, product):
        '''
            Returns one and only one instance of the data for a given quali_flow.
            Will throw if multiple instances are found in db.
            Will return a default item, if nothing exists.
        '''
        items = self.get_data_for_qualification_flow(quali_flow_type, product)
        if(len(items) == 0):
            data = QualificationFlowDatum()
            data.product = product
            return data
        elif(len(items) == 1):
            return items[0]
        else:
            raise Exception("Multiple items for qualification flow, where only one is allowed")

    def add_or_update_qualification_flow_data(self, quali_flow_data):
        '''
            Inserts a given set of qualification flow data into the database,
            updating any already existing data with the same "name" field. Note
            that we expect a "type" field to be present.
        '''
        QualificationFlowDatum.add_or_update_qualification_flow_data(self.get_session(), quali_flow_data)
        self.parent.database_changed.emit(TableId.Flow())

    def delete_qualification_flow_instance(self, quali_flow_data):
        QualificationFlowDatum.remove(self.get_session(), quali_flow_data)
        self.parent.database_changed.emit(TableId.Flow())

    def insert_program(self, name, hardware, base, target, usertext, sequencer_typ, temperature, definition, owner_name, order, test_target):
        for index, test in enumerate(definition['sequence']):
            base_test_name = test['name']
            self.add_test_target(name, test_target, hardware, base, base_test_name, True, False)

        Program.add(self.get_session(), name, hardware, base, target, usertext, sequencer_typ, temperature, definition, owner_name, order, test_target)
        self._insert_sequence_informations(owner_name, name, definition)

        self.parent.database_changed.emit(TableId.Flow())

    def _insert_sequence_informations(self, owner_name, prog_name, definition):
        for index, test in enumerate(definition['sequence']):
            # ToDo: Why protocol version 4?
            Sequence.add_sequence_information(self.get_session(), owner_name, prog_name, test['name'], index, test)

    def update_program(self, name, hardware, base, target, usertext, sequencer_typ, temperature, definition, owner_name, test_target):
        self._update_test_targets_list(name, test_target, hardware, base, definition)

        Program.update(self.get_session(), name, hardware, base, target, usertext, sequencer_typ, temperature, owner_name, test_target)

        self._delete_program_sequence(name, owner_name)
        self._insert_sequence_informations(owner_name, name, definition)

        self.parent.database_changed.emit(TableId.Flow())

    def _get_tests_for_target(self, hardware, base, test_target):
        return [test.test for test in TestTarget.get_tests(self.get_session(), hardware, base, test_target)]

    def _update_test_targets_list(self, program_name, test_target, hardware, base, definition):
        tests = []
        for test in definition['sequence']:
            test.pop('is_valid', None)
            test_name = test['name']
            tests.append(test_name)

        tests.sort()
        available_tests = self._get_tests_for_target(hardware, base, test_target)
        available_tests.sort()

        diff = set(tests) - set(available_tests)
        for test_name in diff:
            self.add_test_target(program_name, test_target, hardware, base, test_name, True, False)

        diff = set(available_tests) - set(tests)
        for test_name in diff:
            self.remove_test_target(test_target, test_name, hardware, base)

    def _delete_program_sequence(self, prog_name, owner_name):
        Sequence.remove_program_sequence(self.get_session(), prog_name, owner_name)

    def _generate_program_name(self, program_name, index):
        prog_name = program_name[:-1]
        return prog_name + str(index)

    def delete_program(self, program_name, owner_name, program_order):
        self._remove_test_targets_for_test_program(program_name)

        Program.remove(self.get_session(), program_name, owner_name)
        Sequence.remove_for_program(self.get_session(), program_name)

        for index in range(program_order + 1, self.get_program_owner_element_count(owner_name) + 1):
            new_name = self._generate_program_name(program_name, index)
            Program.update_program_order_and_name(self.get_session(), new_name, index - 1, owner_name, index)

            name = self._generate_program_name(program_name, index + 1)
            Sequence.update_progname(self.get_session(), name, owner_name, new_name)

        self.parent.database_changed.emit(TableId.Flow())

    def _remove_test_targets_for_test_program(self, prog_name):
        tests = set([seq.test for seq in Sequence.get_for_program(self.get_session(), prog_name)])
        targets = [target.name for target in TestTarget.get_for_program(self.get_session(), prog_name)]
        TestTarget.remove_for_test_program(self.get_session(), prog_name)

        for target, test in zip(targets, tests):
            self.parent.test_target_deleted.emit(target, test)

    def move_program(self, program_name, owner_name, program_order, is_up):
        session = self.get_session()
        prog = Program.get_by_name_and_owner(session, program_name, owner_name)
        order = prog.prog_order  # result[0]
        prog_id = prog.id  # result[1]

        count = self.get_program_owner_element_count(owner_name)
        if is_up:
            if order == 0:
                return
            prev = order - 1
        else:
            if order == count - 1:
                return
            prev = order + 1

        self._update_elements(program_name, owner_name, order, prev, prog_id)

        self.parent.database_changed.emit(TableId.Flow())

    def _get_program_ids_from_sequence(self, prog_name, owner_name):
        return Sequence.get_for_program(self.get_session(), prog_name)

    def _update_program_name_for_sequence(self, new_prog_name, owner_name, ids):
        Sequence.update_program_name_for_sequence(self.get_session(), new_prog_name, owner_name, ids)

    def _update_sequence(self, prog_name, new_prog_name, owner_name, prog_id):
        prog_ids = [prog_id.id for prog_id in self._get_program_ids_from_sequence(prog_name, owner_name)]
        new_prog_ids = [prog_id.id for prog_id in self._get_program_ids_from_sequence(new_prog_name, owner_name)]

        self._update_program_name_for_sequence(new_prog_name, owner_name, prog_ids)
        self._update_program_name_for_sequence(prog_name, owner_name, new_prog_ids)

        self.parent.database_changed.emit(TableId.Flow())

    def _get_test_program_name(self, prog_order, owner_name):
        return Program.get_by_order_and_owner(self.get_session(), prog_order, owner_name).prog_name

    def _update_test_program_name(self, prog_name, new_name):
        Program.update_program_name(self.get_session(), prog_name, new_name)

    def _update_elements(self, prog_name, owner_name, prev_order, order, id):
        neighbour = self._get_test_program_name(order, owner_name)
        self._update_sequence(prog_name, neighbour, owner_name, id)

        self._update_program_order(owner_name, prev_order, order, neighbour)
        self._update_program_order_neighbour(owner_name, order, prev_order, prog_name, id)

    def _update_program_order_neighbour(self, owner_name, prev_order, order, new_name, id):
        Program._update_program_order_neighbour(self.get_session(), owner_name, prev_order, order, new_name, id)

    def _update_program_order(self, owner_name, prev_order, order, new_name):
        Program._update_program_order(self.get_session(), owner_name, prev_order, order, new_name)

    def get_program_owner_element_count(self, owner_name):
        return Program.get_program_owner_element_count(self.get_session(), owner_name)

    def get_programs_for_owner(self, owner_name):
        return Program.get_programs_for_owner(self.get_session(), owner_name)

    def get_program_configuration_for_owner(self, owner_name, prog_name):
        prog = Program.get_by_name_and_owner(self.get_session(), prog_name, owner_name)
        retval = {}
        retval.update({"hardware": prog.hardware})
        retval.update({"base": prog.base})
        retval.update({"target": prog.target})
        retval.update({"usertext": prog.usertext})
        retval.update({"sequencer_type": prog.sequencer_type})
        if prog.sequencer_type == 'Fixed Temperature':
            retval.update({"temperature": str(pickle.loads(prog.temperature))})
        else:
            retval.update({"temperature": ','.join(str(x) for x in pickle.loads(prog.temperature))})

        return retval

    def get_program_test_configuration(self, program, owner):
        sequence = Sequence.get_for_program(self.get_session(), program)
        retval = []
        for sequence_entry in sequence:
            retval.append(sequence_entry.get_definition())

        return retval

    def get_tests_for_program(self, prog_name, owner_name):
        return Sequence.get_for_program(self.get_session(), prog_name)

    def get_programs_for_node(self, type, name):
        all = Program.get_programs_for_target(self.get_session(), name)
        retval = {}

        for row in all:
            if retval.get(row.owner_name) and row.prog_name in retval[row.owner_name]:
                continue

            retval.setdefault(row.owner_name, []).append(row.prog_name)

        return retval

    def get_programs_for_test(self, test_name):
        all = Sequence.get_programs_for_test(self.get_session(), test_name)
        retval = {}

        for row in all:
            if retval.get(row.owner_name) and row.prog_name in retval[row.owner_name]:
                continue

            retval.setdefault(row.owner_name, []).append(row.prog_name)

        return retval

    def get_programs_for_hardware(self, hardware):
        data = [(program.prog_name, program.owner_name) for program in Program.get_programs_for_hardware(self.get_session(), hardware)]
        retval = {}

        for row in data:
            retval.setdefault(row[1], []).append(row[0])

        return retval

    def add_test_target(self, prog_name, name, hardware, base, test, is_default, is_enabled=False):
        if TestTarget.exists(self.get_session(), name, hardware, base, test, prog_name):
            return

        TestTarget.add(self.get_session(), name, prog_name, hardware, base, test, is_default, is_enabled)
        self.parent.database_changed.emit(TableId.Test())

    def remove_test_target(self, name, test, hardware, base):
        TestTarget.remove(self.get_session(), name, test, hardware, base)
        self.parent.test_target_deleted.emit(name, test)

    def set_test_target_default_state(self, name, hardware, base, test, is_default):
        if not is_default:
            self._generate_test_target_file(name, test, hardware, base)

        TestTarget.set_default_state(self.get_session(), name, hardware, base, test, is_default)
        self.parent.database_changed.emit(TableId.TestItem())

    def set_test_target_state(self, name, hardware, base, test, is_enabled):
        TestTarget.toggle(self.get_session(), name, hardware, base, test, is_enabled)

    def is_test_target_set_to_default(self, name, hardware, base, test):
        return TestTarget.get(self.get_session(), name, hardware, base, test).is_default

    def get_available_test_targets(self, hardware, base, test):
        return [test.name for test in TestTarget.get_for_hardware_base_test(self.get_session(), hardware, base, test)]

    def get_test_targets_for_program(self, prog_name):
        return TestTarget.get_for_program(self.get_session(), prog_name)

    def get_tests_for_test_target(self, hardware, base, test):
        return self.get_available_test_targets(hardware, base, test)

    # TODO: use following arguments after fixing test behaviour (hardware, base)
    def _generate_test_target_file(self, target_name, test, hardware, base):
        testdefinition = Test.get(self.get_session(), test, hardware, base).get_definition()
        testdefinition['base'] = base
        testdefinition['base_class'] = test
        testdefinition['name'] = target_name
        testdefinition['hardware'] = hardware
        from ATE.spyder.widgets.coding.generators import test_target_generator
        test_target_generator(self.project_directory, testdefinition)

    def get_available_testers(self):
        # TODO: implement once the pluggy stuff is in place.
        return ['SCT', 'CT']

    def _get_dependant_objects_for_node(self, node, dependant_objects, node_type):
        tree = {}
        for definition in dependant_objects:
            # name = tables[definition].name
            query = f"SELECT * FROM {definition} WHERE {node_type} = ?"
            self.cur.execute(query, (node,))
            for row in self.cur.fetchall():
                if tree.get(definition) is None:
                    tree[definition] = [row[0]]
                else:
                    tree[definition].append(row[0])

        return tree

    def get_dependant_objects_for_hardware(self, hardware):
        dependant_objects = ['devices', 'dies', 'products', 'tests']

        tree = {}
        for dep in dependant_objects:
            all = tables[dep].get_all_for_hardware(self.get_session(), hardware)
            for row in all:
                if tree.get(dep) is None:
                    tree[dep] = [row.name]
                else:
                    tree[dep].append(row.name)

        programs = {'programs': self.get_programs_for_hardware(hardware)}
        if not programs['programs']:
            return tree

        tree.update(programs)
        return tree

    def get_dependant_objects_for_maskset(self, maskset):
        dependant_objects = ['dies']
        tree = {}
        for dep in dependant_objects:
            all = tables[dep].get_all_for_maskset(self.get_session(), maskset)
            for row in all:
                if tree.get(dep) is None:
                    tree[dep] = [row.name]
                else:
                    tree[dep].append(row.name)

        return tree

    def get_dependant_objects_for_die(self, die):
        objs = {}
        deps = {'devices': []}
        devices = self.get_device_names()
        for name in devices:
            definition = self.get_device_definition(name)['dies_in_package']
            if die in definition:
                deps['devices'].append(name)

        if deps['devices']:
            objs.update(deps)

        programs = {'programs': self.get_programs_for_node('target', die)}
        if programs['programs']:
            objs.update(programs)

        return objs

    def get_dependant_objects_for_package(self, package):
        deps = {'devices': []}
        devices = self.get_device_names()
        for name in devices:
            definition = self.get_device_package(name)
            if package in definition:
                deps['devices'].append(name)

        if len(deps['devices']) == 0:
            return {}

        return deps

    def get_dependant_objects_for_device(self, device):
        deps = {'products': []}
        product = self.get_products_for_device(device)
        deps['products'] = product

        if len(deps['products']) == 0:
            return {}

        return deps

    def get_dependant_objects_for_test(self, test):
        return self.get_programs_for_test(test)

    def _get_state(self, name, type):
        return tables[type].get(self.get_session(), name).is_enabled

    def _update_state(self, name, state, type):
        tables[type].update_state(self.get_session(), name, state)

    def get_hardware_state(self, name):
        return self._get_state(name, 'hardwares')

    def update_hardware_state(self, name, state):
        self._update_state(name, state, 'hardwares')
        if not state:
            self.parent.hardware_removed.emit(name)
        else:
            self.parent.hardware_changed.emit(name)

    def get_maskset_state(self, name):
        return Maskset.get(self.get_session(), name).is_enabled

    def update_maskset_state(self, name, state):
        Maskset.update_state(self.get_session(), name, state)

    def get_die_state(self, name):
        return Die.get(self.get_session(), name).is_enabled

    def update_die_state(self, name, state):
        self._update_state(name, state, 'dies')
        self.parent.update_target.emit()

    def get_package_state(self, name):
        return self._get_state(name, 'packages')

    def update_package_state(self, name, state):
        self._update_state(name, state, 'packages')

    def get_device_state(self, name):
        return Device.get(self.get_session(), name).is_enabled

    def update_device_state(self, name, state):
        self._update_state(name, state, 'devices')
        self.parent.update_target.emit()

    def get_product_state(self, name):
        return Product.get(self.get_session(), name).is_enabled

    def update_product_state(self, name, state):
        self._update_state(name, state, 'products')

    def get_test_state(self, name, hardware, base):
        return Test.get(self.get_session(), name, hardware, base).is_enabled

    def update_test_state(self, name, state):
        self._update_state(name, state, 'tests')

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if not self.con:
            return

        self.con.close()

    def delete_item(self, type, name):
        tables[type].remove(self.get_session(), name)
        self.parent.database_changed.emit(TableId.Definition())

    def last_project_setting(self):
        return os.path.join(self.project_directory, '.lastsettings')

    def _store_settings(self):
        import json
        settings = {'settings': {'hardware': self.active_hardware,
                                 'base': self.active_base,
                                 'target': self.active_target}
                    }

        with open(self.last_project_setting(), 'w') as f:
            json.dump(settings, f, indent=4)

    def load_project_settings(self):
        import json
        settings_path = self.last_project_setting()
        if not os.path.exists(settings_path):
            return '', '', ''

        with open(settings_path, 'r') as f:
            settings = json.load(f)
            settings = settings['settings']
            return settings['hardware'], settings['base'], settings['target']
