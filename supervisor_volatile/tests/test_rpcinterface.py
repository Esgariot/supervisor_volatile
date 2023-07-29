import sys
import unittest

import supervisor
from supervisor.xmlrpc import Faults as SupervisorFaults
from supervisor.states import SupervisorStates, ProcessStates

from supervisor_volatile.rpcinterface import Faults as VolatileFaults

from supervisor.tests.base import DummySupervisor
from supervisor.tests.base import DummyPConfig, DummyProcess
from supervisor.tests.base import DummyPGroupConfig, DummyProcessGroup

class TestRPCInterface(unittest.TestCase):

    # Fault Constants

    def test_volatile_fault_names_dont_clash_with_supervisord_fault_names(self):
        supervisor_faults = self.attrDictWithoutUnders(SupervisorFaults)
        volatile_faults = self.attrDictWithoutUnders(VolatileFaults)

        for name in supervisor_faults.keys():
            self.assertTrue(volatile_faults.get(name) is None)

    def test_volatile_fault_codes_dont_clash_with_supervisord_fault_codes(self):
        supervisor_fault_codes = self.attrDictWithoutUnders(SupervisorFaults).values()
        volatile_fault_codes = self.attrDictWithoutUnders(VolatileFaults).values()

        for code in supervisor_fault_codes:
            self.assertFalse(code in volatile_fault_codes)

    # Constructor

    def test_ctor_assigns_supervisord(self):
        supervisord = DummySupervisor()
        interface = self.makeOne(supervisord)

        self.assertEqual(supervisord, interface.supervisord)

    # Factory

    def test_make_volatile_rpcinterface_factory(self):
        from supervisor_volatile import rpcinterface

        supervisord = DummySupervisor()
        interface = rpcinterface.make_volatile_rpcinterface(supervisord)

        self.assertTrue(isinstance(interface,
            rpcinterface.SupervisorVolatileRPCInterface))
        self.assertEqual(supervisord, interface.supervisord)

    # Updater

    def test_updater_raises_shutdown_error_if_supervisord_in_shutdown_state(self):
        supervisord = DummySupervisor(state = SupervisorStates.SHUTDOWN)
        interface = self.makeOne(supervisord)

        self.assertRPCError(SupervisorFaults.SHUTDOWN_STATE,
                            interface.getAPIVersion)

    # API Method volatile.getAPIVersion()

    def test_getAPIVersion_can_be_disabled(self):
        supervisord = DummySupervisor()
        interface = self.makeOne(supervisord, whitelist='foo,bar')

        self.assertRPCError(VolatileFaults.NOT_IN_WHITELIST,
                            interface.getAPIVersion)

    def test_getAPIVersion_returns_api_version(self):
        supervisord = DummySupervisor()
        interface = self.makeOne(supervisord)

        version = interface.getAPIVersion()
        self.assertEqual('getAPIVersion', interface.update_text)

        from supervisor_volatile.rpcinterface import API_VERSION
        self.assertEqual(version, API_VERSION)

    # API Method volatile.getGroupNames()

    def test_getGroupNames_can_be_disabled(self):
        supervisord = DummySupervisor()
        interface = self.makeOne(supervisord, whitelist='foo,bar')

        self.assertRPCError(VolatileFaults.NOT_IN_WHITELIST,
                            interface.getGroupNames)

    def test_getGroupNames_returns_empty_array_when_no_groups(self):
        supervisord = DummySupervisor()
        interface = self.makeOne(supervisord)

        names = interface.getGroupNames()
        self.assertTrue(isinstance(names, list))
        self.assertEqual(0, len(names))

    def test_getGroupNames_returns_group_names(self):
        pconfig = DummyPConfig(None, 'foo', '/bin/foo')
        gconfig = DummyPGroupConfig(None, pconfigs=[pconfig])
        pgroup = DummyProcessGroup(gconfig)

        pgroups = {'foo': pgroup, 'bar': pgroup}
        supervisord = DummySupervisor(process_groups = pgroups)
        interface = self.makeOne(supervisord)

        names = interface.getGroupNames()
        self.assertTrue(isinstance(names, list))
        self.assertEqual(2, len(names))
        names.index('foo')
        names.index('bar')

    # API Method volatile.addEmptyGroup()

    def test_addEmptyGroup_can_be_disabled(self):
        supervisord = DummySupervisor()
        interface = self.makeOne(supervisord, whitelist='foo,bar')
        
        self.assertRPCError(VolatileFaults.NOT_IN_WHITELIST, 
                            interface.addEmptyGroup, 'foo', 999)
    
    def test_addEmptyGroup_raises_bad_name_when_group_name_already_exists(self):
        pconfig = DummyPConfig(None, 'foo', '/bin/foo')
        gconfig = DummyPGroupConfig(None, pconfigs=[pconfig])
        pgroup = DummyProcessGroup(gconfig)

        supervisord = DummySupervisor(process_groups = {'existing_group': pgroup})
        interface = self.makeOne(supervisord)
        
        self.assertRPCError(SupervisorFaults.BAD_NAME,
                            interface.addEmptyGroup,
                            'existing_group', 42)

    def test_addEmptyGroup_raises_incorrect_parameters_when_priority_not_int(self):
        supervisord = DummySupervisor()
        interface = self.makeOne(supervisord)
        
        self.assertRPCError(SupervisorFaults.INCORRECT_PARAMETERS,
                            interface.addEmptyGroup,
                            'new_group', 'not_an_int')

    def test_addEmptyGroup_adds_and_configures_new_group(self):
        supervisord = DummySupervisor()
        interface = self.makeOne(supervisord)
        self.assertTrue(interface.addEmptyGroup('new_group', 42))
        
        new_group = supervisord.process_groups.get('new_group')
        self.assertTtrue(isinstance(new_group, 
            supervisor.process.ProcessGroup))

        config = new_group.config
        self.assertEquals('new_group', config.name)
        self.assertEquals(42, config.priority)
        self.assertEquals([], config.process_configs)
    
    # API Method volatile.addProgramToGroup()

    def test_addProgramToGroup_can_be_disabled(self):
        supervisord = DummySupervisor()
        interface = self.makeOne(supervisord, whitelist='foo,bar')

        self.assertRPCError(VolatileFaults.NOT_IN_WHITELIST,
                            interface.addProgramToGroup, 'grp', 'prog', {})

    def test_addProgramToGroup_raises_bad_name_when_group_doesnt_exist(self):
        pconfig = DummyPConfig(None, 'foo', '/bin/foo')
        gconfig = DummyPGroupConfig(None, pconfigs=[pconfig])
        pgroup = DummyProcessGroup(gconfig)

        supervisord = DummySupervisor(process_groups = {'foo': pgroup})
        interface = self.makeOne(supervisord)

        self.assertRPCError(SupervisorFaults.BAD_NAME,
                            interface.addProgramToGroup,
                            'nonexistant_group', 'foo', {})

    def test_addProgramToGroup_raises_bad_name_when_process_already_exists(self):
        pconfig = DummyPConfig(None, 'process_that_exists', '/bin/foo')
        gconfig = DummyPGroupConfig(None, pconfigs=[pconfig])
        pgroup = DummyProcessGroup(gconfig)

        supervisord = DummySupervisor(process_groups = {'group_name': pgroup})
        supervisord.options = supervisor.options.ServerOptions()
        interface = self.makeOne(supervisord)

        poptions = {'command': '/usr/bin/find /'}
        self.assertRPCError(SupervisorFaults.BAD_NAME,
                            interface.addProgramToGroup,
                            'group_name', 'process_that_exists', poptions)

    def test_addProgramToGroup_raises_incorrect_params_when_poptions_is_not_dict(self):
        pconfig = DummyPConfig(None, 'foo', '/bin/foo')
        gconfig = DummyPGroupConfig(None, pconfigs=[pconfig])
        pgroup = DummyProcessGroup(gconfig)

        supervisord = DummySupervisor(process_groups = {'group_name': pgroup})
        supervisord.options = supervisor.options.ServerOptions()
        interface = self.makeOne(supervisord)

        bad_poptions = 42
        self.assertRPCError(SupervisorFaults.INCORRECT_PARAMETERS,
                            interface.addProgramToGroup,
                            'group_name', 'new_process', bad_poptions)

    def test_addProgramToGroup_raises_incorrect_params_when_poptions_is_invalid(self):
        pconfig = DummyPConfig(None, 'foo', '/bin/foo')
        gconfig = DummyPGroupConfig(None, pconfigs=[pconfig])
        pgroup = DummyProcessGroup(gconfig)

        supervisord = DummySupervisor(process_groups = {'group_name': pgroup})
        supervisord.options = supervisor.options.ServerOptions()

        interface = self.makeOne(supervisord)

        poptions_missing_command = {}
        self.assertRPCError(SupervisorFaults.INCORRECT_PARAMETERS,
                            interface.addProgramToGroup,
                            'group_name', 'new_process', poptions_missing_command)

    def test_addProgramToGroup_adds_new_process_to_supervisord_processes(self):
        pconfig = DummyPConfig(None, 'foo', '/bin/foo')
        gconfig = DummyPGroupConfig(None, pconfigs=[pconfig])
        pgroup = DummyProcessGroup(gconfig)
        pgroup.processes = {}

        supervisord = DummySupervisor(process_groups = {'group_name': pgroup})
        supervisord.options = supervisor.options.ServerOptions()

        interface = self.makeOne(supervisord)

        poptions = {'command': '/usr/bin/find /'}
        self.assertTrue(interface.addProgramToGroup('group_name', 'new_process', poptions))
        self.assertEqual('addProgramToGroup', interface.update_text)

        process = pgroup.processes['new_process']

        self.assertTrue(isinstance(process, supervisor.process.Subprocess))
        self.assertEqual('/usr/bin/find /', process.config.command)

    def test_addProgramToGroup_adds_new_process_config_to_group(self):
        pconfig = DummyPConfig(None, 'foo', '/bin/foo')
        gconfig = DummyPGroupConfig(None, pconfigs=[pconfig])
        pgroup = DummyProcessGroup(gconfig)
        pgroup.processes = {}

        supervisord = DummySupervisor(process_groups = {'group_name': pgroup})
        supervisord.options = supervisor.options.ServerOptions()

        interface = self.makeOne(supervisord)

        poptions = {'command': '/usr/bin/find /'}
        self.assertTrue(interface.addProgramToGroup('group_name', 'new_process', poptions))
        self.assertEqual('addProgramToGroup', interface.update_text)

        config = pgroup.config.process_configs[1]
        self.assertEqual('new_process', config.name)
        self.assertTrue(isinstance(config, supervisor.options.ProcessConfig))

    def test_addProgramToGroup_uses_process_name_from_options(self):
        gconfig = DummyPGroupConfig(None, pconfigs=[])
        pgroup = DummyProcessGroup(gconfig)
        pgroup.processes = {}

        supervisord = DummySupervisor(process_groups = {'group_name': pgroup})
        supervisord.options = supervisor.options.ServerOptions()

        interface = self.makeOne(supervisord)

        poptions = {'process_name': 'renamed', 'command': '/usr/bin/find /'}
        self.assertTrue(interface.addProgramToGroup('group_name', 'new_process', poptions))
        self.assertEqual('addProgramToGroup', interface.update_text)

        config = pgroup.config.process_configs[0]
        self.assertEqual('renamed', config.name)
        self.assertTrue(pgroup.processes.get('new_process') is None)
        self.assertTrue(isinstance(pgroup.processes.get('renamed'),
          supervisor.process.Subprocess))

    def test_addProgramToGroup_adds_all_processes_resulting_from_program_options(self):
        gconfig = DummyPGroupConfig(None, pconfigs=[])
        pgroup = DummyProcessGroup(gconfig)
        pgroup.processes = {}

        supervisord = DummySupervisor(process_groups = {'group_name': pgroup})
        supervisord.options = supervisor.options.ServerOptions()

        interface = self.makeOne(supervisord)

        poptions = {'command': '/usr/bin/find /',
                    'process_name': 'find_%(process_num)d',
                    'numprocs': 3}
        self.assertTrue(interface.addProgramToGroup('group_name', 'new_process', poptions))
        self.assertEqual('addProgramToGroup', interface.update_text)

        self.assertEqual(3, len(pgroup.config.process_configs))
        self.assertEqual(3, len(pgroup.processes))

    # API Method volatile.removeProcessFromGroup()

    def test_removeProcessFromGroup_can_be_disabled(self):
        supervisord = DummySupervisor()
        interface = self.makeOne(supervisord, whitelist='foo,bar')

        self.assertRPCError(VolatileFaults.NOT_IN_WHITELIST,
                            interface.removeProcessFromGroup, 'group', 'process')

    def test_removeProcessFromGroup_raises_bad_name_when_group_doesnt_exist(self):
        pconfig = DummyPConfig(None, 'foo', '/bin/foo')
        gconfig = DummyPGroupConfig(None, pconfigs=[pconfig])
        pgroup = DummyProcessGroup(gconfig)

        supervisord = DummySupervisor(process_groups = {'group_name': pgroup})
        interface = self.makeOne(supervisord)

        self.assertRPCError(SupervisorFaults.BAD_NAME,
                            interface.removeProcessFromGroup,
                            'nonexistant_group_name', 'process_name')

    def test_removeProcessFromGroup_raises_bad_name_when_process_does_not_exist(self):
        pconfig = DummyPConfig(None, 'foo', '/bin/foo')
        gconfig = DummyPGroupConfig(None, pconfigs=[pconfig])
        pgroup = DummyProcessGroup(gconfig)
        pgroup.processes = {}

        supervisord = DummySupervisor(process_groups = {'group_name': pgroup})
        interface = self.makeOne(supervisord)

        self.assertRPCError(SupervisorFaults.BAD_NAME,
                            interface.removeProcessFromGroup,
                            'group_name', 'nonexistant_process_name')

    def test_removeProcessFromGroup_raises_still_running_when_process_has_pid(self):
        pconfig = DummyPConfig(None, 'foo', '/bin/foo')
        process = DummyProcess(pconfig)
        process.pid = 42

        gconfig = DummyPGroupConfig(None, pconfigs=[pconfig])
        pgroup = DummyProcessGroup(gconfig)
        pgroup.processes = { 'process_with_pid': process }

        supervisord = DummySupervisor(process_groups = {'group_name': pgroup})
        interface = self.makeOne(supervisord)

        self.assertRPCError(SupervisorFaults.STILL_RUNNING,
                            interface.removeProcessFromGroup,
                            'group_name', 'process_with_pid')

    def test_removeProcessFromGroup_transitions_process_group(self):
        pconfig = DummyPConfig(None, 'foo', '/bin/foo')
        process = DummyProcess(pconfig, ProcessStates.EXITED)

        gconfig = DummyPGroupConfig(None, pconfigs=[pconfig])
        pgroup = DummyProcessGroup(gconfig)
        pgroup.processes = { 'process_name': process }

        supervisord = DummySupervisor(process_groups = {'group_name': pgroup})
        interface = self.makeOne(supervisord)

        result = interface.removeProcessFromGroup('group_name', 'process_name')
        self.assertTrue(result)
        self.assertTrue(pgroup.transitioned)

    def test_removeProcessFromGroup_deletes_the_process(self):
        pconfig = DummyPConfig(None, 'foo', '/bin/foo')
        process = DummyProcess(pconfig, ProcessStates.STOPPED)

        gconfig = DummyPGroupConfig(None, pconfigs=[pconfig])
        pgroup = DummyProcessGroup(gconfig)
        pgroup.processes = { 'process_name': process }

        supervisord = DummySupervisor(process_groups = {'group_name': pgroup})
        interface = self.makeOne(supervisord)

        result = interface.removeProcessFromGroup('group_name', 'process_name')
        self.assertTrue(result)
        self.assertTrue(pgroup.processes.get('process_name') is None)
        self.assertEqual('removeProcessFromGroup', interface.update_text)

    # API Method volatile.log()

    def test_log_can_be_disabled(self):
        supervisord = DummySupervisor()
        interface = self.makeOne(supervisord, whitelist='foo,bar')

        self.assertRPCError(VolatileFaults.NOT_IN_WHITELIST,
                            interface.log, 'message')

    def test_log_write_message_when_level_is_string(self):
        supervisord = DummySupervisor()
        interface = self.makeOne(supervisord)

        result = interface.log('hello', 'info')
        self.assertTrue(result)
        result = interface.log('there', 'INFO')
        self.assertTrue(result)
        self.assertEqual('log', interface.update_text)

        logger = supervisord.options.logger
        self.assertEqual(['hello', 'there'], logger.data)

    def test_log_write_message_when_level_is_integer(self):
        supervisord = DummySupervisor()
        interface = self.makeOne(supervisord)

        from supervisor.loggers import LevelsByName
        result = interface.log('hello', LevelsByName.INFO)
        self.assertTrue(result)

        logger = supervisord.options.logger
        self.assertEqual(['hello'], logger.data)

    def test_log_raises_incorrect_parameters_when_level_is_bad(self):
        supervisord = DummySupervisor()
        interface = self.makeOne(supervisord)

        for bad_level in ['bad_level', 9999, None]:
            self.assertRPCError(SupervisorFaults.INCORRECT_PARAMETERS,
                                interface.log, 'hello', bad_level)

    # Helpers Methods

    def getTargetClass(self):
        from supervisor_volatile.rpcinterface import SupervisorVolatileRPCInterface
        return SupervisorVolatileRPCInterface

    def makeOne(self, *arg, **kw):
        return self.getTargetClass()(*arg, **kw)

    def attrDictWithoutUnders(self, obj):
        """ Returns the __dict__ for an object with __unders__ removed """
        attrs = {}
        for k, v in obj.__dict__.items():
            if not k.startswith('__'): attrs[k] = v
        return attrs

    # Helper Assertion Methods

    def assertRPCError(self, code, callable, *args, **kw):
        try:
            callable(*args, **kw)
        except supervisor.xmlrpc.RPCError as e:
            self.assertEqual(e.code, code)
        else:
            self.fail('RPCError was never raised')


def test_suite():
    return unittest.findTestCases(sys.modules[__name__])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
