import maya.cmds as mc
def fileConnector(placeNode, fileNode):
    mc.connectAttr (placeNode + '.coverage', fileNode + '.coverage')
    mc.connectAttr (placeNode + '.translateFrame', fileNode + '.translateFrame')
    mc.connectAttr (placeNode + '.rotateFrame', fileNode + '.rotateFrame')
    mc.connectAttr (placeNode + '.mirrorU', fileNode + '.mirrorU')
    mc.connectAttr (placeNode + '.mirrorV', fileNode + '.mirrorV')
    mc.connectAttr (placeNode + '.stagger', fileNode + '.stagger')
    mc.connectAttr (placeNode + '.wrapU', fileNode + '.wrapU')
    mc.connectAttr (placeNode + '.wrapV', fileNode + '.wrapV')
    mc.connectAttr (placeNode + '.repeatUV', fileNode + '.repeatUV')
    mc.connectAttr (placeNode + '.offset', fileNode + '.offset')
    mc.connectAttr (placeNode + '.rotateUV', fileNode + '.rotateUV')
    mc.connectAttr (placeNode + '.noiseUV', fileNode + '.noiseUV')
    mc.connectAttr (placeNode + '.vertexUvOne', fileNode + '.vertexUvOne')
    mc.connectAttr (placeNode + '.vertexUvTwo', fileNode + '.vertexUvTwo')
    mc.connectAttr (placeNode + '.vertexUvThree', fileNode + '.vertexUvThree')
    mc.connectAttr (placeNode + '.vertexCameraOne', fileNode + '.vertexCameraOne')
    mc.connectAttr (placeNode + '.outUV', fileNode + '.uv')
    mc.connectAttr (placeNode + '.outUvFilterSize', fileNode + '.uvFilterSize')

def aiAssembler(selMeshTransform):
    #=============creacion============
    selMeshShape = mc.listRelatives(selMeshTransform, typ='shape')
    geoBaseName = (selMeshTransform.split ('__'))[0]
    shaderName = geoBaseName + '__SHD'
    
    shapeNode = mc.ls(sl = True, dag = True, s = True)
    shaderEng = mc.listConnections(shapeNode , type = "shadingEngine")
    assignedShader = mc.ls(mc.listConnections(shaderEng ), materials = True)

    if assignedShader[0] == shaderName:
        print selMeshTransform + ' ya tiene shader!'
        pass
    else:
        AIshader = mc.shadingNode ('aiStandardSurface', n=shaderName, asShader=True)
        remapColorNode = mc.shadingNode ('remapColor', n='remapColor_base_' + geoBaseName, asUtility=True)
        remapValueNode = mc.shadingNode ('remapValue', n='remapVal_roughness_' + geoBaseName, asUtility=True)
        
        bump = mc.shadingNode ('bump2d', n='bump2D_' + geoBaseName, asTexture=True)
        mc.setAttr (bump + '.bumpInterp', 1)
        #place2DBump = mc.shadingNode ('place2dTexture', n='place2D_Bump', asUtility=True)
        
        metalnessFile = mc.shadingNode ('file', n='file_metalness_' + geoBaseName, asTexture=True)
        mc.setAttr (metalnessFile + '.colorSpace', 'Raw', typ='string')
        mc.setAttr (metalnessFile + '.alphaIsLuminance', 1)
        mc.setAttr (metalnessFile + '.uvTilingMode', 3) #UDIM
        place2DMet = mc.shadingNode ('place2dTexture', n='place2D_Met', asUtility=True)
        
        roughnessFile = mc.shadingNode ('file', n='file_roughness_' + geoBaseName, asTexture=True)
        mc.setAttr (roughnessFile + '.colorSpace', 'Raw', typ='string')
        mc.setAttr (roughnessFile + '.alphaIsLuminance', 1)
        mc.setAttr (roughnessFile + '.uvTilingMode', 3)
        place2DRough = mc.shadingNode ('place2dTexture', n='place2D_Rough', asUtility=True)
        
        baseColorFile = mc.shadingNode ('file', n='file_baseColor_' + geoBaseName, asTexture=True)
        mc.setAttr (baseColorFile + '.uvTilingMode', 3)
        place2DBaseColor = mc.shadingNode ('place2dTexture', n='place2D_BaseColor', asUtility=True)
        
        normalFile = mc.shadingNode ('file', n='file_normal_' + geoBaseName, asTexture=True)
        mc.setAttr (normalFile + '.colorSpace', 'Raw', typ='string')
        mc.setAttr (normalFile + '.alphaIsLuminance', 1)
        mc.setAttr (normalFile + '.uvTilingMode', 3)
        place2DNormal = mc.shadingNode ('place2dTexture', n='place2D_Normal', asUtility=True)
        
        layeredTextureDiff = mc.shadingNode ('layeredTexture', n='Diff_baseColor_' + geoBaseName, asTexture=True)
        
        #==========conecciones============
        fileConnector (place2DMet, metalnessFile)
        fileConnector (place2DBaseColor, baseColorFile)
        fileConnector (place2DRough, roughnessFile)
        fileConnector (place2DNormal, normalFile)
        
        mc.connectAttr (normalFile + '.outAlpha', bump + '.bumpValue')
        mc.connectAttr (bump + '.outNormal', AIshader + '.normalCamera')
        
        mc.connectAttr (roughnessFile + '.outAlpha', remapValueNode + '.inputValue')
        mc.connectAttr (remapValueNode + '.outValue', AIshader + '.specularRoughness')
        
        mc.connectAttr (baseColorFile + '.outColor', remapColorNode + '.color')
        mc.connectAttr (remapColorNode + '.outColor', layeredTextureDiff + '.inputs[0].color')
        mc.connectAttr (layeredTextureDiff + '.outColor', AIshader + '.baseColor')
        
        mc.connectAttr (metalnessFile + '.outAlpha', AIshader + '.metalness')
        
        shadingGroup = mc.sets (renderable=True, noSurfaceShader=True, empty=True, name=AIshader + 'SG')
        mc.sets (selMeshTransform, e=True, forceElement=AIshader + 'SG')
        mc.connectAttr (AIshader + '.outColor', shadingGroup + '.surfaceShader')
        
def main():
    selMeshList = mc.ls(sl=True, typ='transform')
    noSuffixMeshes = []
    for selMeshTransform in selMeshList:
        #if not '__MSH' in selMeshTransform:
        if selMeshTransform.endswith('__MSH') == False:
            noSuffixMeshes.append (selMeshTransform)
            mc.warning ('NOMENCLATE BIEN EL MESH!!!')
            mc.confirmDialog( title='OJO!', message= selMeshTransform + ' NO nomenclado!', bgc=[1,0.7,0.7], button=['OK'], cancelButton='OK' )
        elif ':' in selMeshTransform:
            mc.warning ('Mesh dentro de NAMESPACE!!!')
            mc.confirmDialog( title='ATENTI!', message='Mesh dentro de NAMESPACE!', bgc=[1,0.3,0.3],button=['OK'], cancelButton='OK' )
        else:
            aiAssembler(selMeshTransform)
    mc.select (noSuffixMeshes)
