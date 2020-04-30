from typing import Dict
 
from nornir import InitNornir 
from nornir.core.inventory import Host 
from nornir.plugins.functions.text import print_result 
from nornir.plugins.tasks.networking import napalm_get 
from nornir.core.task import AggregatedResult, MultiResult, Result, Task 
 
from nornir.plugins.tasks.networking import netmiko_send_command 
from ntc_templates.parse import parse_output 
import json 

MAC_TO_FIND = '00:0B:BE:E6:51:80' # Vlan800 + Vlan3843 very OLD WS-C3550-24-SMI 
#MAC_TO_FIND = '00:13:21:B1:B6:CF' # SERVER
#MAC_TO_FIND = '0C:85:25:6B:C2:42' # Vlan3843 3750G-48  
#MAC_TO_FIND = '0C:85:25:6B:C2:41' # Vlan906  3750G-48  
#MAC_TO_FIND = '00:16:C8:35:6F:20' # Gi1/0/3 Vlan3843 LAB-3750G-48  

# Sorry added this Class from Nornir/Napalm example to get Dict result ¯\_(ツ)_/¯
class PrintResult: 
    def task_started(self, task: Task) -> None: 
        #print(f">>> starting: {task.name}") 
        pass 

    def task_completed(self, task: Task, result: AggregatedResult) -> None: 
        #print(f">>> completed: {task.name}") 
        pass 
 
    def task_instance_started(self, task: Task, host: Host) -> None: 
        pass 
 
    def task_instance_completed( 
        self, task: Task, host: Host, result: MultiResult 
    ) -> None: 
        #print(f"  - {host.name}: - {result.result}") 
        pass 
 
    def subtask_instance_started(self, task: Task, host: Host) -> None: 
        pass  # to keep example short and sweet we ignore subtasks 
 
    def subtask_instance_completed( 
        self, task: Task, host: Host, result: MultiResult 
    ) -> None: 
        pass  # to keep example short and sweet we ignore subtasks 
 
class SaveResultToDict: 
    def __init__(self, data: Dict[str, None]) -> None: 
        self.data = data 
                     
    def task_started(self, task: Task) -> None: 
        self.data[task.name] = {} 
        self.data[task.name]["started"] = True 
 
    def task_completed(self, task: Task, result: AggregatedResult) -> None: 
        self.data[task.name]["completed"] = True 
 
    def task_instance_started(self, task: Task, host: Host) -> None: 
        self.data[task.name][host.name] = {"started": True} 
 
    def task_instance_completed( 
        self, task: Task, host: Host, result: MultiResult 
    ) -> None: 
        self.data[task.name][host.name] = { 
            "completed": True, 
            "result": result.result, 
        } 
 
    def subtask_instance_started(self, task: Task, host: Host) -> None: 
        pass  # to keep example short and sweet we ignore subtasks 
 
    def subtask_instance_completed( 
        self, task: Task, host: Host, result: MultiResult 
    ) -> None: 
        pass  # to keep example short and sweet we ignore subtasks 
 
##### /// START \\\ #####

 
nr = InitNornir(config_file="config.yaml", dry_run=True)   
 
SWPORTS = {} 
interfaces_switchport_data = nr.run(netmiko_send_command, command_string='show interfaces switchport') 
for switch, resuslt in interfaces_switchport_data.items():  
    #print(switch)  
    interfaces_list = parse_output(platform="cisco_ios", command="show interfaces switchport", data=str(resuslt[0])) 
    SWPORTS[switch] = interfaces_list 
 
 
mac_address_table_data = {} 
nr_with_processors = nr.with_processors([SaveResultToDict(mac_address_table_data), PrintResult()]) 
nr_with_processors.run(task=napalm_get, getters=["mac_address_table"]) 
 
interfaces_data = {} 
nr_with_processors = nr.with_processors([SaveResultToDict(interfaces_data), PrintResult()]) 
nr_with_processors.run(task=napalm_get, getters=["interfaces"]) 
 
print("TRYING TO FIND MAC: {}".format(MAC_TO_FIND))  

MACDB = {} 
for switch in SWPORTS.keys():  
    MACDB[switch] = {} 
 
for port in interfaces_data['napalm_get'][switch]["result"]["interfaces"]: 
    if interfaces_data['napalm_get'][switch]['result']['interfaces'][port]['mac_address'] == MAC_TO_FIND: 
        MACDB[switch][port] = 'static SVI' 
 
for switch in mac_address_table_data['napalm_get'].keys(): 
    if switch not in ['started', 'completed']: 
        #print(switch) 
        for item in mac_address_table_data['napalm_get'][switch]["result"]["mac_address_table"]: 
            #print(item['mac']) 
            if MAC_TO_FIND == item['mac']: 
                #print(item) 
                if item['interface'] == '': 
                    # !!! need this term e.g. for very OLD 3550 because all L3 Vlan interfaces have the same MAC !!! 
                    for SVI in interfaces_data['napalm_get'][switch]["result"]["interfaces"]: 
                        if interfaces_data['napalm_get'][switch]['result']['interfaces'][SVI]['mac_address'] == MAC_TO_FIND:
                            MACDB[switch][str(SVI)] = 'static SVI' 
                else: 
                    for swinterface in SWPORTS[switch]: 
                        if swinterface['interface'] == item['interface']:  
                            #print (swinterface['admin_mode']) 
                            MACDB[switch][item['interface']] = swinterface['admin_mode'] 
 
#print("All collected DB with your MAC {}".format(MAC_TO_FIND)) 
#print(MACDB) 
#print("*" * 40) 

for sw in MACDB: 
    for port in MACDB[sw]: 
        if "static" in MACDB[sw][port]: 
            print("Found your MAC {} on {} port {}".format(MAC_TO_FIND, sw, port)) 
