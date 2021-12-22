[comment]: # "Auto-generated SOAR connector documentation"
# Arbor APS

Publisher: Splunk  
Connector Version: 2\.0\.8  
Product Vendor: Arbor Networks  
Product Name: Arbor Networks APS  
Product Version Supported (regex): "\.\*"  
Minimum Product Version: 4\.9\.39220  

This app integrates with Arbor Networks APS to execute containment and corrective actions

### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a Arbor Networks APS asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**server\_url** |  required  | string | Server URL \(e\.g\. https\://10\.10\.10\.10\)
**verify\_server\_cert** |  optional  | boolean | Verify server certificate
**username** |  required  | string | Username
**password** |  required  | password | Password

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration  
[list ips](#action-list-ips) - List all IPs on the outbound Blocklist or Allowlist  
[block ip](#action-block-ip) - Add an IP to the outbound Blocklist  
[unblock ip](#action-unblock-ip) - Remove an IP from the outbound Blocklist  
[allow ip](#action-allow-ip) - Add an IP to the outbound Allowlist  
[unallow ip](#action-unallow-ip) - Remove an IP from the outbound Allowlist  

## action: 'test connectivity'
Validate the asset configuration for connectivity using supplied configuration

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'list ips'
List all IPs on the outbound Blocklist or Allowlist

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**list** |  required  | List | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.list | string | 
action\_result\.data\.\*\.hosts\.\*\.hostAddress | string |  `ip` 
action\_result\.data\.\*\.hosts\.\*\.updateTime | numeric | 
action\_result\.summary\.num\_ips | numeric | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'block ip'
Add an IP to the outbound Blocklist

Type: **contain**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** |  required  | IP Address | string |  `ip` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.ip | string |  `ip` 
action\_result\.data\.\*\.hostAddress | string |  `ip` 
action\_result\.data\.\*\.updateTime | numeric | 
action\_result\.data\.\*\.updatetimeISO | string | 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'unblock ip'
Remove an IP from the outbound Blocklist

Type: **correct**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** |  required  | IP Address | string |  `ip` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.ip | string |  `ip` 
action\_result\.data | string | 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'allow ip'
Add an IP to the outbound Allowlist

Type: **contain**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** |  required  | IP Address | string |  `ip` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.ip | string |  `ip` 
action\_result\.data | string | 
action\_result\.data\.\*\.hostAddress | string |  `ip` 
action\_result\.data\.\*\.updateTime | numeric | 
action\_result\.data\.\*\.updatetimeISO | string | 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'unallow ip'
Remove an IP from the outbound Allowlist

Type: **correct**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** |  required  | IP Address | string |  `ip` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.ip | string |  `ip` 
action\_result\.data | string | 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric | 