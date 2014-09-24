# -*-coding:utf-8-*-
#########################################################
#
# Copyright (c) 2005, Southpaw Technology
#                     All Rights Reserved
#
# PROPRIETARY INFORMATION.  This software is proprietary to
# Southpaw Technology, and is not to be reproduced, transmitted,
# or disclosed in any way without written permission.
#
#
#

__all__ = ['MayaException', 'Maya', 'Maya85', 'MayaNodeNaming']


import sys, types, re, os

from maya_environment import *
from pyasm.application.common import NodeData, Common, Application, AppException

class MayaException(AppException):
    pass


class MayaNodeNaming:
    def __init__(my, node_name=None):
        my.node_name = node_name
        my.namespace = ''
        my.asset_code = ''
        if my.node_name:
            if my.node_name.find(":") != -1:
                my.has_namespace_flag = True
                my.namespace, my.asset_code = my.node_name.split(":",1)
            else:
                my.has_namespace_flag = False
                my.asset_code = my.namespace = my.node_name
        if my.namespace:
            my.namespace = my.namespace.replace(' ', '_')


    def get_asset_code(my):
        return my.asset_code

    def set_asset_code(my, asset_code):
        my.asset_code = asset_code


    #TODO: deprecate the instance methods
    def get_instance(my):
        return my.namespace

    def set_instance(my, namespace):
        my.has_namespace_flag = True
        my.namespace = namespace

    def get_namespace(my):
        return my.namespace

    def set_namespace(my, namespace):
        my.has_namespace_flag = True
        my.namespace = namespace

    def set_node_name(my, node_name):
        my.node_name = node_name

    # HACK: this is REALLY bad code.  FIXME: Tactic needs a much better
    # node naming implementation.  Functions should pass around the naming
    # object, not the node_name
    def get_node_name(my):
        if not my.node_name:
            if my.asset_code:
                my.node_name = "%s:%s" % (my.namespace, my.asset_code)
            else: # user-created node has no asset code
                my.node_name = my.namespace
                return my.node_name
            app = Maya.get()
            if not app.node_exists(my.node_name):
                my.node_name = my.namespace
            if not app.node_exists(my.node_name):
                my.node_name = my.asset_code

        return my.node_name

    def build_node_name(my):
        node_name = "%s:%s" % (my.namespace, my.asset_code)
        # prevent problems when no namespace or asset code is given
        if node_name == ":":
            node_name = ""
        return node_name


    def has_instance(my):
        return my.has_namespace_flag

    def has_namespace(my):
        return my.has_namespace_flag

pymel = None
maya = None

class Maya(Application):
    '''encapsulates the pymaya plugin and its functionality.  It also provides
    a possbility to created a distributed maya server that will not be
    run on the web server'''

    APPNAME = "maya"

    def __init__(my, init=False):
        my.name = "maya"

        try:
            exec("import pymel as pymel")
        except Exception, e:
            print "exception"
            raise MayaException(e)

        if init == True:
            pymel.maya_init("default")

        super(Maya, my).__init__()

        my.mel("loadPlugin -quiet animImportExport")


    def is_tactic_node(my, node):
        return NodeData.is_tactic_node(node)

    def new_session(my):
        return mel("file -f -new")


    def get_node_naming(my, node_name=None):
        return MayaNodeNaming(node_name)



    def mel(my, cmd, verbose=None):
        if my.buffer_flag == True:
            my.buffer.append(cmd)
        else:
            if not pymel:
                exec("import pymel as pymel", globals(), locals())
            if verbose == True or (verbose == None and my.verbose == True):
                print "->", cmd
            return pymel.mel(cmd)



    def cleanup(my):
        exec("import pymel as pymel")
        pymel.maya_cleanup()



    # Common maya operations
    #   These abstract and interface to maya version so that implementations
    # for each version of maya can made.  Versions between Maya can be
    # highly volatile for in terms of stability and functionality.
    # This attempts to protect tactic from changes between Maya versions.
    # As few basic operations as possible into maya are defined to simplify
    # porting.

    def get_var(my, name):
        value = mel('$%s = $%s' % (name, name) )
        #value = value.replace("||", "/")
        #print "value: ", name, value
        return value

        #获取node_name的节点类型
    def get_node_type(my, node_name):
        type = mel('nodeType "%s"' % node_name)
        if not type:
            raise MayaException("Node '%s' does not exist" % node_name)
        return type

        #获取node_name的父物体名称
    def get_parent(my, node_name):
        parent = mel('firstParentOf %s' % node_name)
        return parent

        #获取一个节点下所有的子物体(获取类型根据type='transform'来决定)
    def get_children(my, node_name, full_path=True, type='transform', recurse=False):
        '''Get the children nodes. type: transform, shape'''
        full_path_switch = ''
        recurse_switch = ''
        if full_path:
	    full_path_switch = '-fullPath'
        if recurse:
            recurse_switch = '-ad'
        children = mel('listRelatives %s %s -type %s "%s"' %(full_path_switch, recurse_switch, type, node_name))
        if children:
            return list(children)
        else:
            return []

    #给节点的属性设置数值或者字符串
    # action functions
    def set_attr(my, node, attr, value, attr_type=""):
        if attr_type == "string":
            mel('setAttr %s.%s -type "string" "%s"' % (node,attr,value))
        # maya doesn't work too well with this
        # elif attr_type:
        #    mel('setAttr %s.%s -type %s %s' % (node,attr, attr_type, value))
        else:
            '''attr_type is optional for numeric value'''
            mel('setAttr %s.%s %s' % (node,attr,value))


            #选择场景内的物体
    # selection functions
    # 仅仅只选择指定名称节点,目的是避免选择集选择会跳过该节点而直接全部选择到里面的内容
    def select(my, node):
        mel('select -noExpand "%s"' % node )

        #加选指定的节点
    def select_add(my, node):
        mel('select -noExpand -add "%s"' % node )

        #清空选择
    def select_none(my):
        mel('select -cl')

    #清空当前选择,重新选择指定节点
    def select_restore(my, nodes):
        my.select_none()
        for node in nodes:
            my.select_add(node)

            #选择当前物体下的所有子物体
    def select_hierarchy(my, node):
        mel("select -hi %s" %node)

        #import进来一个maya文件
    # interaction with files
    def import_file(my, path, namespace=":"):
        if namespace in ['',":"]:
            mel('file -pr -import "%s"' % (path) )
        else:
            mel('file -namespace "%s" -pr -import "%s"' % (namespace, path) )

            #reference进来一个maya文件
    def import_reference(my, path, namespace=":"):
        if namespace in ['',":"]:
            mel('file -pr -reference "%s"' % (path) )
        else:
            mel('file -namespace "%s" -pr -reference "%s"' % (namespace, path) )

            #查询一个节点是否是reference
            #这里的reference -q命令已经更改为referenceQuery命令
    def is_reference(my, node_name):
        is_ref = mel('referenceQuery -inr "%s"' % node_name)
        if is_ref:
            return True
        else:
            return False


            #替换一个reference参考路径
    def replace_reference(my, node_name, path, top_reference=True):
        '''load using references. If top reference is False,
            it will replace the sub reference if any (To be verified!)'''
        switch = '-rfn'
        if top_reference:
            switch = '%s -tr' %switch
        ref_node = mel('referenceQuery %s "%s"' % (switch, node_name ))
        #ref_node = mel('referenceQuery -rfn "%s"' % ref_path )

        # replace the reference
        return mel('file -loadReference "%s" "%s"' % (ref_node, path) )


        #判断一个物体的属性是否有K帧
    def is_keyed(my, node_name, attr):
        is_keyed = mel('connectionInfo -id %s.%s' %(node_name, attr))
        if is_keyed:
            return True
        else:
            return False

            #导入动画文件
    def import_anim(my, path, namespace=":"):
        mel('file -import -type animImport "%s"' % path)

        #在一行或者一页字符串中提取出节点名称,属性名称,属性值,属性类型,然后调用set_attr函数进行属性设置
    def import_static(my, buffer, node_name):
        lines = buffer.split("\n")
        pat = re.compile('(.+) -type (.+) -default (.+) -value (.+)')
        for line in lines:
            m = pat.match(line)
            if m:
                attr, attr_type, value = m.group(1), m.group(2),  m.group(4)
                my.set_attr(node_name, attr, value, attr_type)



                #导出动画文件
    def export_anim(my, path, namespace=":"):
        mel('file -force -exportAnim -op "-heirarchy none" -type "animExport" "%s"' % path)
        return path




        #删除指定的节点
    def delete(my, node_name):
        # set has no namespace
        if my.is_set(node_name):
            mel('delete "%s"' % node_name)
            return

            #清理并删除名字空间
        # clean out and remove the namespace
        naming = my.get_node_naming(node_name)
        instance = naming.get_instance()
        if naming.has_instance():
            my.set_namespace(instance)
            # if the namespace is already removed, skip
            current = mel("namespaceInfo -cur")
            if current == instance:

                garbage_nodes = mel("namespaceInfo -listNamespace")
                if garbage_nodes:
                    for garbage_node in garbage_nodes:
                        if not my.is_reference(node_name) and "lightLinker" in garbage_node:
                            my.delete_nondeletable_node(garbage_node)
                        else:
                            mel('delete "%s"' % garbage_node)



        my.set_namespace()

        my.remove_namespace(instance)

        if my.is_reference(node_name):
            #这里的reference -q命令已经更改为referenceQuery命令
            reference_file = mel('referenceQuery -filename "%s"' % node_name)
            mel('file -removeReference "%s"' % reference_file)

        else:
            # delete an imported node
            mel('delete "%s"' % node_name)


    # file utilities

    #打开一个maya文件
    def load(my, path):
        if path.endswith(".ma"):
            mel('file -f -options "v=0"  -typ "mayaAscii" -o "%s"' % path)
        else:
            mel('file -f -options "v=0"  -typ "mayaBinary" -o "%s"' % path)
        return path

        #更改文件的保存名称或者保存地址,方便保存文件
    def rename(my, path):
        '''rename the file so that "save" will go to that directory'''
        print "renaming: ", path
        if path.endswith("/") or path.endswith("\\"):
            path = "%suntitled.ma" % path
        elif not path:
            path = "untitled.ma"
        #elif not path.endswith(".ma"):
        #    path = "%s.ma" % path

        mel('file -rename "%s"' % path)
        if path.endswith(".ma"):
            mel('file -type "mayaAscii"')
        elif path.endswith(".mb"):
            mel('file -type "mayaBinary"')

            #保存文件
    def save(my, path, file_type=None):
        if not file_type:
            file_type="mayaAscii"

        if file_type == "mayaAscii" and not path.endswith(".ma"):
            path, ext = os.path.splitext(path)
            path = "%s.ma" % path
        elif file_type == "mayaBinary" and not path.endswith(".mb"):
            path, ext = os.path.splitext(path)
            path = "%s.mb" % path

        my.rename(path)
        mel('file -force -save -type %s' % file_type)
        return path

        #检测文件保存的类型(.ma和.mb)是否正确
    def save_node(my, node_name, dir=None, type="mayaAscii", as_ref=False ):
        naming = my.get_node_naming(node_name)
        asset_code = naming.get_asset_code()

        if dir == None:
            path = "%s" % (asset_code)
        else:
            path = "%s/%s" % (dir, asset_code)
        if type == "mayaAscii" and not path.endswith(".ma"):
            path, ext = os.path.splitext(path)
            path = "%s.ma" % path
        elif type == "mayaBinary" and not path.endswith(".mb"):
            path, ext = os.path.splitext(path)
            path = "%s.mb" % path


        return my.save(path, file_type=type)

        #获取当前maya的文件路径
    def get_file_path(my):
        # switching because file -q -loc does not return anything until you
        # actually save
        #path = mel("file -q -loc")
        #if path == "unknown":
        paths = mel("file -q -list")
        if type(paths) in (types.ListType, types.TupleType):
            path = paths[0]

        if path.endswith("untitled"):
            return ""

        return path


        #导出节点(框架函数,由下列子函数进行调用)
    def export_node(my, node_names, context, dir=None, type="mayaAscii", as_ref=False, preserve_ref=True, filename='', instance=None ):
        '''exports top node(s) in maya'''

        asset_code = ''
        #isinstance是Python中的一个内建函数,语法,isinstance(object, classinfo) ,
        #如果参数object是classinfo的实例，或者object是classinfo类的子类的一个实例， 返回True。
        #如果object不是一个给定类型的的对象， 则返回结果总是False。
        #isinstance(1, int),True
        #isinstance(1.0, float),True
        #class myClass:pass;test = myClass();isinstance(test, myClass);True
        if isinstance(node_names, list):
            if not list:
                raise MayaException('The list to export is empty')
            my.select_none()
            for node_name in node_names:
                my.select_add(node_name)
            # we just pick a node_name for asset_code which is part of
            # a filename, if used
            if my.is_tactic_node(node_names[0]):
                naming = my.get_node_naming(node_names[0])
                instance = naming.get_instance()
            else:
                instance = node_names[0]

        else:
            my.select( node_names )
            naming = my.get_node_naming(node_names)
            instance = naming.get_instance()

        export_mode = "-es"
        if as_ref:
            export_mode = "-er"

        if preserve_ref:
            export_mode = '-pr %s' %export_mode

        # find the desired extension
        if type == "mayaAscii":
            type_key = type
            ext = "ma"
        elif type == "mayaBinary":
            type_key = type
            ext = "mb"
        elif type == "collada":
            type_key = "COLLADA exporter"
            ext = "dae"
        elif type == "obj":
            type_key = "OBJexport"
            ext = "obj"
        else:
            type_key = "mayaAscii"
            ext = "ma"


        # build the file name
        if filename:
            filename, old_ext = os.path.splitext(filename)
        elif not instance:
            filename = "untitled"
        else:
            filename = instance

        filename = "%s.%s" % (filename, ext)
        filename = Common.get_filesystem_name(filename)

        if dir == None:
            path = mel('file -rename "%s"' % filename )
        else:
            path = "%s/%s" % (dir, filename)

        mel('file -rename "%s"' % path )
        cmd = 'file -force -op "v=0" %s -type "%s"' % (export_mode, type_key)
        print "cmd: ", cmd
        mel(cmd)

        return path

        #导出dae类型的数据
    def export_collada(my, node_name, dir=None):
        type = "COLLADA exporter"
        return my.export_node(node_name, dir, type)

        #导出obj类型的数据
    def export_obj(my, node_name, dir=None):
        type = "OBJexport"
        return my.export_node(node_name, dir, type)

        #移除removeReference文件
    def delete_nondeletable_node(my, node_name):
        #TODO keep current selection
        my.select_none()

        tmp_dir = "%s/temp" % MayaEnvironment.get().get_tmpdir()
        reference_file =  my.export_node(node_name, tmp_dir, as_ref=True)
        mel('file -removeReference "%s"' % reference_file)


    # namespace commands
    # 设置当前的名字空间
    def set_namespace(my, namespace=":"):
        mel('namespace -set "%s"' % namespace)

        #创建一个新的名字空间
    def add_namespace(my, namespace):
        if not my.namespace_exists(namespace):
            mel('namespace -add "%s"' % namespace)

            #删除指定的名字空间,该名字空间必须为空
    def remove_namespace(my, namespace):
        mel('namespace -removeNamespace "%s"' % namespace)

        #查询指定的名字空间是否存在
    def namespace_exists(my, namespace):
        return mel('namespace -exists "%s"' % namespace)

        #namespaceInfo查询名字空间的相关信息
        #默认为列出所有的名字空间
    def get_namespace_info(my, option='-lon'):
        return mel('namespaceInfo %s' %option)

        #重命名一个节点
    def rename_node(my, node_name, new_name):
        '''it assumes the new name is under the root namespace'''
        return mel('rename %s %s' %(node_name, new_name))

    # set functions
    # set集相关的操作,列出maya所以的set集,然后进行字符匹配处理
    # 将skinCluster,cluster,tweakSet这三类set集数据剔除出去
    # 目测只留下人工创建的选择集set
    def get_sets(my):
        #all_sets = mel('listSets -allSets')
        # change to this.  The above does not give the full namespace name
        all_sets = set(mel('ls -type objectSet'))
        #maya内没有delightShapeSet这个类型的节点,因此需要将下列语句屏蔽
        """
        delight_set = set()
        try:
            delight_list = mel('ls -type delightShapeSet')
            if delight_list:
                delight_set = set(delight_list)
        except Exception, e:
            pass
        """
        ignore_set = set(['defaultLightSet', 'defaultObjectSet']).union(delight_set)
        #ignore_set = set(['defaultLightSet', 'defaultObjectSet'])
        render_set = set()
        deformer_set = set()


        # shadingEngine is strangely a subset of -type objectSet in Maya 7 at least
        render_set_list = mel('ls -type shadingEngine')
        deformer_set_list = mel('listSets -type 2')

        if render_set_list:
            render_set = set(render_set_list)
        if deformer_set_list:
            deformer_set = set(deformer_set_list)
        all_sets = all_sets - render_set - deformer_set - ignore_set

        # remove any set with the suffix of the deformer_set_list


        sets = []
        if deformer_set_list:
            regex = '|'.join(['skinCluster\d*Set','cluster\d*Set', 'tweakSet\d*'] )
            deformer_pat = re.compile(r'(%s)$' %regex)
            sets = [ x for x in all_sets if not deformer_pat.search(x) ]
        else:
            sets = list(all_sets)

        '''

        for x in all_sets:
            # cannot use this because sets do not usually have this at the
            # beginning
            #elif not my.attr_exists(x, "tacticNodeData"):
            #    continue

            sets.append(x)
        '''

        return sets

    #判断指定的set集是否存在
    def is_set(my, node_name):
        if node_name in my.get_sets():
            return True
        else:
            return False

    #创建一个set集
    def create_set(my, node_name):
        if not my.node_exists(node_name):
            mel('sets -n "%s"' % node_name)

    #添加新的节点物体到指定的一个set集
    def add_to_set(my, set_name, node_name):
        # a quick way of avoiding the add set to set warning msg on shot load
        if node_name in [set_name, ':%s'%set_name]:
            return
        mel('sets -add "%s" "%s"' % (set_name, node_name) )

    #获取一个指定的set集内的所有节点
    def get_nodes_in_set(my, set_name):
        nodes = mel('sets -q "%s"' % set_name )
        if not nodes:
            return []
        else:
            return list(nodes)





    # information retrieval functions.  Requires an open Maya session
    # 判断一个节点是否存在
    def node_exists(my,node):
        node = mel("ls %s" % node)
        if node == None:
            return False
        else:
            return True

    #列出场景内指定类型的所以物体
    def get_nodes_by_type(my, type):
        return mel("ls -type %s" % type)


    #获取场景内第一个选中的物体
    def get_selected_node(my):
        nodes = mel("ls -sl")
        if nodes:
            return nodes[0]
        else:
            return None

    #获取场景内所有被选中的物体
    def get_selected_nodes(my):
        nodes = mel("ls -sl")
        return nodes

    #获取最顶级被选中的转换节点
    def get_selected_top_nodes(my):
        return mel("ls -sl -as")


    #获取顶级转换节点的名称
    #例如[u'|front', u'|group5|group1', u'|group5|group2', u'|persp', u'|side', u'|top']会返回[u'group5']
    def get_top_nodes(my):
        # maya 7.0 bug: "ls -as" produces garbage
        nodes  = mel("ls -tr -l")

        top_level = []
        for node in nodes:
            node = node.lstrip('|')

            if node.count("|") > 0:
                continue

            # ignore default cameras
            if node in ['persp', 'front', 'top', 'side']:
                continue

            top_level.append(node)

        return top_level



    #获取所有tactic相关节点
    def get_tactic_nodes(my, top_node=None):
        '''Much simpler method to get TACTIC nodes using new definition of
        TACTIC nodes
        '''
        nodes = mel('ls "*:tactic_*"')
        if not nodes:
            return []
        tactic_nodes = []
        for node in nodes:
            # TODO: check if nodes have the attribute "tacticNodeData"

            tactic_nodes.append(node)
        return tactic_nodes


    #recursive=true是进行循环匹配,会匹配所有名字空间内的相关节点,反之就只匹配相同名字的物体
    #该程序组目测是返回,指定节点或者场景内的全部包含"tacticNodeData"属性的references物体
    def get_reference_nodes(my, top_node=None, sub_references=False, recursive=False):
        '''Want to get all of the tactic nodes that exist under a single
        entity.  This entity can be one of 3 items.  The maya file itself,
        a set containing a number of top nodes or a single top node.  These
        are treated as the containment entity'''
        # FIXME: misnamed ... this gets all of the tactic nodes, not all the
        # reference nodes

        # get a list of nodes that could possibly be Tactic nodes

        #获取大纲内顶级节点名称,变量类型为列表型
        if top_node == None:
            # find all of the top nodes in the file
            top_nodes = my.get_top_nodes()
        elif my.get_node_type(top_node) == "objectSet":
            # if this is a set: get all of the nodes in the set
            top_nodes = mel('sets -q -nodesOnly "%s"' % top_node)
        else:
            top_nodes = [top_node]

        # ensure that top_nodes is a list, because mel isn't very consistent
        # with returned types.
        if type(top_nodes) not in (types.ListType, types.TupleType):
            top_nodes = [top_nodes]

        # this is a top transform node. we look down the hierarchy for
        # tactic nodes.  Only nodes with one namespace greater than the
        # top node are considered

        #判断指定节点名称包含几层名字空间
        num_parts = 0
        if not recursive:
            if top_node:
                parts = top_node.split(":")
                num_parts = len(parts)
            else:
                num_parts = 1


        # look through transforms
        # 获取大纲内所有的顶级转换节点或者指定的某个顶级转换节点内的全部物体名称,存放在nodes内
        node_type = "transform"
        nodes = []
        for node in top_nodes:
            tmp_nodes = mel('ls -type %s -recursive true -dag -allPaths "%s"' % (node_type, node) )
            if not tmp_nodes:
                continue

            if type(tmp_nodes) in (types.ListType, types.TupleType):
                nodes.extend(tmp_nodes)
            else:
                nodes.append(tmp_nodes)

        references = []
        if not nodes:
            return references

        for node in nodes:
            # only consider nodes that have one namespace greater than the
            # top node.
            # 如果名字空间数量大于指定节点的名字空间数量,就跳过该节点
            if node and not recursive:
                parts = node.split(":")
                if len(parts) > num_parts + 1:
                    continue

            # sub refs are always maya references
            # 如果有节点是reference节点,同时该节点存在"tacticNodeData"属性,则添加到references列表变量内
            #这里的reference -q命令已经更改为referenceQuery命令
            is_ref = mel('referenceQuery -isNodeReferenced "%s"' % node)
            if is_ref:
                # found a potential node ...
                # make sure this has a tacticNodeData attribute
                if my.attr_exists(node, "tacticNodeData"):
                    references.append(node)


        return references

        #返回一个reference文件的路径
        #这里的reference -q命令已经更改为referenceQuery命令
        #
    def get_reference_path(my, node):
        path = mel("referenceQuery -filename %s" % node)
        if path:
            return path
        else:
            return ""


            #创建一个新的节点
    def add_node(my, type, node_name, unique=False):
        return mel("createNode -n %s %s" % (node_name, type) )


    # attributes
    # 给节点添加一个自定义属性
    def add_attr(my, node, attribute, type="long"):
        # do nothing if it already exists
        if my.attr_exists(node,attribute):
            return
        if type == "string":
            return mel('addAttr -ln "%s" -dt "string" %s' % (attribute, node) )
        else:
            return mel('addAttr -ln "%s" -at "long" %s' % (attribute, node) )

            #判断一个节点的属性是否存在
    def attr_exists(my, node, attribute):
        # don't bother being verbose with this one
        return my.mel("attributeExists %s \"%s\"" % (attribute, node), verbose=False )

        #返回一个节点的属性的值
    def get_attr(my, node, attribute):
        if not my.attr_exists(node, attribute):
            return ""
        value = mel("getAttr %s.%s" % (node, attribute) )
        # never return None for an attr
        if value == None:
            return ""
        else:
            return value

            #返回一个节点的属性的数据类型
    def get_attr_type(my, node, attribute):
        ''' get the attribute type e.g. int, string, double '''
        if not my.attr_exists(node, attribute):
            return ""
        value = mel("getAttr -type %s.%s" % (node, attribute) )
        # never return None for an attr
        if not value:
            return ""
        else:
            return value

            #列出一个节点所以能K帧的属性和自定义属性
    def get_all_attrs(my, node):
        keyable = mel("listAttr -keyable %s" % node )
        user_defined = mel("listAttr -userDefined %s" % node)
        attrs = []
        attrs.extend(keyable)
        if user_defined:
            attrs.extend(user_defined)
        return attrs

        #返回一个节点属性的初始默认值,无视当前数值
    def get_attr_default(my, node, attr):
         return mel("attributeQuery -node %s -listDefault %s" % \
            (node, attr) )



    # layer functions
    # 获取当前场景内所有的渲染层
    def get_all_layers(my):
        '''get all of the render layers'''
        return mel("ls -type renderLayer")

        #返回指定渲染层内的所有节点
    def get_layer_nodes(my, layer_name):
        '''get all of the tactic nodes in a render layer'''
        return mel("editRenderLayerMembers -q %s" % layer_name)







    # MAYA specific functions


    # namespaces
    # these 2 can be replaced with get_namespace_info()
    # 列出当前场景内所以名称空间的名字和全部内容列表
    def get_namespace_contents(my):
        '''retrieves the contents of the current namespac'''
        contents = mel('namespaceInfo -listNamespace')
        return contents

        #只列出所有名字空间名称
    def get_all_namespaces(my):
        return mel('namespaceInfo -listOnlyNamespaces')


        #返回当前工作空间的根目录
    def get_workspace_dir(my):
        return mel("workspace -q -rootDirectory")

        #设置maya的工程目录
    def set_project(my, dir):
        mel('setProject "%s"' % dir)

        #返回当前工程目录的根目录
    def get_project(my):
        return mel("workspace -q -rootDirectory")

        #返回当前maya主界面框的标题,
        #例如Autodesk Maya 2014: D:\project\binding\scenes\zj\test_bind01.mb[*]   ---   curve1
    def get_window_title(my):
        return mel('window -q -title $gMainWindow')

        #编辑当前maya主界面框的标题
    def set_window_title(my, title):
        mel('window -edit -title "%s" $gMainWindow' % title )





    # static functions
    maya = None
    def get():
        # the current version is stored in MayaEnvironment
        env = MayaEnvironment.get()
        return env.get_app()
    get = staticmethod(get)



# importing 8.5 maya module
try:
    import maya as mm
except:
    pass


class Maya85(Maya):
    def __init__(my, init=True):
        my.name = "maya"

        # don't use the Maya constructor
        super(Maya, my).__init__()

        #加载一个animImportExport插件
        my.mel("loadPlugin -quiet animImportExport")


    def mel(my, cmd, verbose=None):
        if my.buffer_flag == True:
            my.buffer.append(cmd)
        else:
            if verbose == True or (verbose == None and my.verbose == True):
                print "->", cmd
            try:
                return mm.mel.eval(cmd)
            except Exception, e:
                if cmd.startswith("MayaManInfo"):
                    print "Warning: ", cmd
                else:
                    print "Error: ", cmd
                    # Let the MEL keep running
                    raise MayaException(cmd)

    # FIXME: reference command is Obsolete
    # 这里的reference -q命令已经更改为referenceQuery命令
    def is_reference(my, node_name):
        is_ref = mel('referenceQuery -inr "%s"' % node_name)
        if is_ref:
            return True
        else:
            return False


    # FIXME: reference command is Obsolete
    # 这里的reference -q命令已经更改为referenceQuery命令
    def get_reference_path(my, node):
        path = mel("referenceQuery -filename %s" % node)
        if path:
            return path
        else:
            return ""




    def cleanup(my):
        '''do nothing'''
        pass


def mel(cmd):
    '''convenience method to get maya object and call mel command'''
    maya = Maya.get()
    return maya.mel(cmd)


