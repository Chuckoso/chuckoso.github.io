#usual imports if needed

def delNamespaces():
    
    currentNS = mc.namespaceInfo( lon=True )
    defaults = ["UI", "shared"]
    while len(currentNS) > len(defaults):
        diff = [item for item in currentNS if item not in defaults]
        for ns in diff:
            if mc.namespace(exists=str(ns)):
                try:
                    mc.namespace(rm=str(ns), mnr=1)
                    currentNS = mc.namespaceInfo( lon=True )
                    #print currentNS
                except Exception, e:
                    defaults.append(ns)
