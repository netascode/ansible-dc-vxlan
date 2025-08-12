# Utility to select the correct REST module based on network_os

def get_rest_module(network_os):
    if network_os == 'cisco.dcnm.dcnm':
        return 'cisco.dcnm.dcnm_rest'
    elif network_os == 'cisco.nd.nd':
        return 'cisco.nd.nd_rest'
    else:
        return None
