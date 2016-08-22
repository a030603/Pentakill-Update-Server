# Binary tree, Red-black tree, AVL tree implementation
# RB tree is binary tree which is logically equivalent to 2, 4 tree
# RB tree is known as more faster for insertion, deletion, but slower
# for retrieval than AVL tree.
# AVL tree is more balanced tree than RB tree, but uses more space
# to store height information.
# For general purposes, RB tree is preferred to AVL tree
import threading

class Node(object):
    def __init__(self, parent=None, left=None, right=None):
        self.parent = parent
        self.left = left
        self.right = right
        
        self.key = None
        self.value = None
        
    def set_key(self, key):
        self.key = key
        
    def set_value(self, value):
        self.value = value
        
    def replace_with_node(self, node):
        self.key = node.key
        self.value = node.value
        
    def is_left(self, node):
        if self.left is node:
            return True
        elif self.right is node:
            return False
        
        print self.left, self.right, node
        print node.left, node.right
        raise Exception("the node is not child of the parent")
    
    # Get sibling node
    # If node has no sibling or parent, returns None
    def sibling(self):
        parent = self.parent
        if parent is None:
            return None
        if parent.is_left(self):
            return parent.right
        else:
            return parent.left
        
class RedBlackNode(Node):
    def __init__(self, parent=None, left=None, right=None, is_red=True):
        super(RedBlackNode, self).__init__(parent, left, right)
        
        self.is_red = is_red
        
    def get_red_child(self):
        if self.left is not None:
            if self.left.is_red:
                return self.left
        if self.right is not None:
            if self.right.is_red:
                return self.right
        return None
    
class AVLNode(Node):
    def __init__(self, parent=None, left=None, right=None, height=1):
        super(AVLNode, self).__init__(parent, left, right)
        
        self.height = height
        
    def renew_height(self):
        heights = self.get_child_heights()
        self.height = max(heights[0], heights[1]) + 1
        assert (abs(heights[0] - heights[1]) < 3)
        return heights
        
    def get_child_heights(self):
        left, right = 0, 0
        if self.left is not None:
            left = self.left.height
        if self.right is not None:
            right = self.right.height
        return (left, right)
    
class BinaryTree(object):
    def __init__(self):
        self.root = None
        self.lock = threading.Lock()
        self.node = Node
        
    def inorder_traverse(self):
        self._inorder_visit(self.root)
        
    def _inorder_visit(self, node):
        if node is None:
            return
        self._inorder_visit(node.left)
        print node.key
        self._inorder_visit(node.right)
        
    # Finds node with key 'key' and
    # returns associated value.
    # If no node is found, returns None
    def retrieve(self, key):
        tup = self._find_node(key)
        
        if tup is None or not tup[0]:
            return None
        else:
            return tup[1].value
        
    # Inserts a node
    # If there were node with same key, returns False.
    # It not, returns True.
    def insert(self, key, value):
        node = self._insert(key, value)
        return node is not None
    
    # If there is no node with key 'key',
    # inserts node and return that node.
    # Otherwise, return None
    def _insert(self, key, value):
        if self.root is None:
            node = self.node()
            node.set_key(key)
            node.set_value(value)
            
            self.root = node
            return node
        
        tup = self._find_node(key)
        if tup[0]:
            return None
        
        node = self.node()
        node.set_key(key)
        node.set_value(value)
        
        parent = tup[1]
        node.parent = parent
        if parent.key > node.key:
            parent.left = node
        else:
            parent.right = node
        return node
        
    # Finds node with key 'key'
    # Returns None when tree is empty
    # Returns (True, node) if found
    # Returns (False, node) if not found.
    # In this case, node is last node looked up
    def _find_node(self, key): 
        if self.root is None:
            return None
        
        parent = self.root
        cur = self.root
        
        while True:
            parent = cur
            if cur.key > key:
                cur = cur.left
            elif cur.key < key:
                cur = cur.right
            else:
                return (True, cur)
            if cur is None:
                return (False, parent)            
    
    # Deletes entry with key 'key'
    # If node found and deleted, returns value.
    # If not found, returns None
    def delete(self, key):
        tup = self._find_node(key)
        if tup is None or not tup[0]:
            return None
        node = tup[1]
        replaced_node = self._find_replace_node(node)
        self._replace_node(node, replaced_node)
        return node.value
    
    def delete_root(self):
        if not self.root:
            return None
        
        return self.delete(self.root.key)
            
    # Replace node 'node' with node 'replace'
    # 'replace' must be child of 'node'
    def _replace_node(self, node, replace):
        if replace is None:
            parent = node.parent
            if parent is None:
                self.root = None
            elif parent.is_left(node):
                parent.left = None
            else:
                parent.right = None
        else:
            parent = replace.parent
            left = replace.left
            right = replace.right
            if parent.is_left(replace):
                if node is parent:
                    parent.left = left
                    parent.right = right
                    if left is not None:
                        left.parent = parent
                    if right is not None:
                        right.parent = parent
                else:
                    parent.left = replace.right
                    if right is not None:
                        right.parent = parent
            else:
                parent.right = replace.right
                if right is not None:
                    right.parent = parent
            node.replace_with_node(replace)
        
    # Returns Node which will replace 'node'
    # If no node can be replaced, returns None
    def _find_replace_node(self, node):
        next_node = self._find_following_node(node)
        if next_node is None:
            return node.left
        else:
            return next_node
    
    # Finds node right next to node 'node'
    # with respect to key order
    # If there is no such node, returns None
    def _find_following_node(self, node):
        cur = node.right
        if cur is None:
            return None
        while True:
            if cur.left is None:
                return cur
            cur = cur.left
            
    def acquire_mutex(self):
        self.lock.acquire()
        
    def release_mutex(self):
        self.lock.release()
      
class BalancedTree(BinaryTree):
    def __init__(self):
        super(BalancedTree, self).__init__()
        
    # n1, n2, n3 must be in increasing order of height in tree.
    # For delete case 3, 
    # n1, n2, n3 must be in n1 < n2 < n3 or n3 < n2 < n1 order
    # Returns tuple (a, b, c)
    def _restructure(self, n1, n2, n3):
        a, b, c, t1, t2, t3, t4 = self._sort_trinode(n1, n2, n3)
        a.left, a.right, c.left, c.right = t1, t2, t3, t4
        b.left, b.right = a, c
        if t1 is not None:
            t1.parent = a
        if t2 is not None:
            t2.parent = a
        if t3 is not None:
            t3.parent = c
        if t4 is not None:
            t4.parent = c
        parent = n3.parent
        a.parent, b.parent, c.parent = b, parent, b
        if parent is None:
            self.root = b
        elif parent.is_left(n3):
            parent.left = b
        else:
            parent.right = b
            
        return (a, b, c)
    
    # n1, n2, n3 must be in increasing order of height in tree
    def _sort_trinode(self, n1, n2, n3):
        if n2.key < n3.key:
            if n1.key < n2.key:
                a, b, c = n1, n2, n3
                t1, t2, t3, t4 = n1.left, n1.right, n2.right, n3.right
            else:
                a, b, c = n2, n1, n3
                t1, t2, t3, t4 = n2.left, n1.left, n1.right, n3.right
        else:
            if n1.key < n2.key:
                a, b, c = n3, n1, n2
                t1, t2, t3, t4 = n3.left, n1.left, n1.right, n2.right
            else:
                a, b, c = n3, n2, n1
                t1, t2, t3, t4 = n3.left, n2.left, n1.left, n1.right
        return (a, b, c, t1, t2, t3, t4)
    
    
class RedBlackTree(BalancedTree):
    def __init__(self):
        super(RedBlackTree, self).__init__()
        
        self.node = RedBlackNode
    
    def insert(self, key, value):
        node = self._insert(key, value)
        if node is None:
            return False
        self._insert_adjustment(node)
        return True
        
    def _insert_adjustment(self, node):
        while True:
            parent = node.parent
            if parent is None:
                self.root = node
                node.is_red = False
                return
            
            if not parent.is_red:
                node.is_red = True
                return
            
            # resolve double red
            grand_parent = parent.parent
            sibling = parent.sibling()
            if sibling is None or not sibling.is_red:
                # case 1: restructure
                self._restructure(self.ADJ_INSERT, node, parent, grand_parent)
                return
            else:
                # case 2: recoloring
                self._recolor(self.ADJ_INSERT, node)
                node = grand_parent
                continue
        
    ADJ_INSERT = 1
    ADJ_DELETE1 = 2
    ADJ_DELETE2 = 3
    ADJ_DELETE3 = 4
    # n1, n2, n3 must be in increasing order of height in tree.
    # For delete case 3, 
    # n1, n2, n3 must be in n1 < n2 < n3 or n3 < n2 < n1 order
    def _restructure(self, type, n1, n2, n3):
        a, b, c = super(RedBlackTree, self)._restructure(n1, n2, n3)
        
        # color adjusting
        if type == self.ADJ_INSERT:
            # insert
            a.is_red, b.is_red, c.is_red = True, False, True
        elif type == self.ADJ_DELETE1:
            # delete case 1
            color = n3.is_red
            a.is_red, b.is_red, c.is_red = False, color, False
        elif type == self.ADJ_DELETE3:
            # delete case 3
            if n3 == a:
                a.is_red, b.is_red, c.is_red = True, False, False
            elif n3 == c:
                a.is_red, b.is_red, c.is_red = False, False, True
            else:
                raise Exception("invalid argument for restructuring")
        else:
            raise Exception("invalid argument for restructuring")
        
        return (a, b, c)
    
    def _recolor(self, type, node):
        if type == self.ADJ_INSERT:
            parent = node.parent
            grand_parent = parent.parent
            sibling = parent.sibling()
            
            node.is_red = True
            parent.is_red = False
            sibling.is_red = False
            grand_parent.is_red = True
        elif type == self.ADJ_DELETE2:
            parent = node.parent
            
            node.is_red = True
            parent.is_red = False
        else:
            raise Exception("invalid argument for recoloring")
        
    def delete(self, key):
        tup = self._find_node(key)
        if tup is None or not tup[0]:
            return None
        node = tup[1]
        replace_node = self._find_replace_node(node)
        adjust_args = self._get_adjust_node(node, replace_node)
        self._delete_adjustment(*adjust_args)
        self._replace_node(node, replace_node)
        return node.value
    
    def _get_adjust_node(self, node, replace_node):
        if replace_node is None:
            return (node.sibling(), node.is_red)
        else:
            return (replace_node.sibling(), replace_node.is_red)
    
    def _delete_adjustment(self, adjust_node, is_red):
        if is_red:
            return
        
        node = adjust_node
        while True:
            if node is None or node.parent is None:
                return
            parent = node.parent
            if node.is_red:
                #assert(not node.right.is_red and not node.left.is_red)
                # Case 3 : restructure and redo
                if parent.is_left(node):
                    child, black = node.left, node.right
                else:
                    child, black = node.right, node.left
                assert(not black.is_red)
                self._restructure(self.ADJ_DELETE3, child, node, parent)
                node = black
                continue
            else:
                red = node.get_red_child()
                if red is None:
                    parent_is_red = parent.is_red
                    # Case 2 : recoloring
                    self._recolor(self.ADJ_DELETE2, node)
                    if parent_is_red:
                        return
                    node = parent.sibling()
                    continue
                else:
                    # Case 1 : restructure
                    self._restructure(self.ADJ_DELETE1, red, node, parent)
                    return
                
    def is_correct_redblack(self):
        return self._traverse_redblack(self.root, True)
    
    # Post order traverse to check if redblack tree invariants are violated
    def _traverse_redblack(self, node, should_black):
        if node is None:
            return True
        
        if should_black and node.is_red:
            return False
        
        a = self._traverse_redblack(node.left, node.is_red)
        b = self._traverse_redblack(node.right, node.is_red)
        
        return a and b
    
class AVLTree(BalancedTree):
    def __init__(self):
        super(AVLTree, self).__init__()
        
        self.node = AVLNode
        
    def _inorder_str_visit(self, node):
        if node is None:
            return
        
        a = ''
        b = ''
        if node.left is not None:
            a = self._inorder_visit(node.left)
        if node.right is not None:
            b = self._inorder_visit(node.right)
        return '( ' + str(a)  + ' ' + str(node.key) + ' ' + str(b) + ' )'
    
    def insert(self, key, value):
        node = self._insert(key, value)
        if node is None:
            return False
        self._insert_adjustment(node)
        return True
    
    def _insert_adjustment(self, node):
        child = None
        while True:
            if node is None or node.parent is None:
                return
            
            parent = node.parent
            parent.renew_height()
            left, right = parent.get_child_heights()
            #print parent.get_child_heights()
            
            if left == right:
                return
            
            if parent.is_left(node):
                node_height, sibling_height = left, right
            else:
                node_height, sibling_height = right, left
            
            if node_height == sibling_height + 1:
                child = node
                node = parent
                continue
            else:
                #print child, node, parent
                self._restructure(child, node, parent)
                return
            
    def _restructure(self, n1, n2, n3):
        a, b, c = super(AVLTree, self)._restructure(n1, n2, n3)
        
        # Here, renew of b must be done last
        a.renew_height()
        c.renew_height()
        b.renew_height()
        
        return (a, b, c)
    
    def delete(self, key):
        tup = self._find_node(key)
        if tup is None or not tup[0]:
            return None
        node = tup[1]
        replace_node = self._find_replace_node(node)
        adjust_node = self._get_adjust_node(node, replace_node)
        self._delete_adjustment(adjust_node)
        self._replace_node(node, replace_node)
        return node.value
    
    def _get_adjust_node(self, node, replace_node):
        if replace_node is None:
            return node
        else:
            return replace_node
    
    def _delete_adjustment(self, node):
        if node is None:
            return
        
        node.height -= 1
        while True:
            if node is None or node.parent is None:
                return
            
            parent = node.parent
            parent.renew_height()
            left, right = parent.get_child_heights()
            
            if parent.is_left(node):
                node_height, sibling_height = left, right
                is_left = True
            else:
                node_height, sibling_height = right, left
                is_left = False
                
            if node_height + 1 == sibling_height:
                return
            elif node_height == sibling_height:
                node = parent
                continue
            else:
                sibling = node.sibling()
                child1 = sibling.right if is_left else sibling.left
                child2 = sibling.left if is_left else sibling.right
                if child1 is not None and child1.height + 1 == sibling.height:
                    a, b, c = self._restructure(child1, sibling, parent)
                    if child2 is None or child2.height == node.height:
                        node = b
                        continue
                    return
                else:
                    a, b, c = self._restructure(child2, sibling, parent)
                    node = b
                    continue
        
    def is_correct_avl(self):
        return self._traverse_avl(self.root)
    
    def _traverse_avl(self, node):
        if node is None:
            return True
        
        left, right = node.get_child_heights()
        if max(left, right) - min(left, right) > 1:
            return False
        
        a = self._traverse_avl(node.left)
        b = self._traverse_avl(node.right)
        
        return a and b

if __name__ == '__main__':
    TREE1 = AVLTree
    TREE2 = RedBlackTree
    def CORRECT1(self):
        return self.is_correct_avl()
    def CORRECT2(self):
        return self.is_correct_redblack()    
    
    
    TREE = TREE2
    CORRECT = CORRECT2
    
    if TREE == TREE1:
        print 'TEST AVL TREE'
    elif TREE == TREE2:
        print 'TEST RED BLACK TREE'
    
    from random import shuffle
    size = 10000
    check_interval = 100
    array = [i for i in range(size)]
    delete = [i for i in range(size / 2)]
    array2 = [i for i in range(size / 2)]
    delete2 = [i for i in range(size)]
    tree = TREE()
    for n in range(10):
        shuffle(array)
        shuffle(array2)
        shuffle(delete)
        shuffle(delete2)
        cnt = 1
        for i in array:
            assert(tree.insert(i, i))
            if cnt % check_interval == 0:
                assert(CORRECT(tree))
            cnt += 1
        print 'Insertion end1'
        
        for i in range(size):
            assert(tree.retrieve(i) is not None)
            
        cnt = 1
        for i in delete:
            assert(tree.delete(i) is not None)
            if cnt % check_interval == 0:
                assert(CORRECT(tree))
                read = delete[cnt:]
                shuffle(read)
                for j in read:
                    assert(tree.retrieve(j) is not None)
            cnt += 1
        print 'Deletion end1'
        
        cnt = 1
        for i in array2:
            assert(tree.insert(i, i))
            if cnt % check_interval == 0:
                assert(CORRECT(tree))
            cnt += 1
        print 'Insertion end2'
        
        for i in range(size):
            assert(tree.retrieve(i) is not None)        
        
        cnt = 1
        for i in delete2:
            assert(tree.delete(i) is not None)
            if cnt % check_interval == 0:
                assert(CORRECT(tree))
                read = delete2[cnt:]
                shuffle(read)
                for j in read:
                    assert(tree.retrieve(j) is not None)
            cnt += 1
        print 'Deletion end2'
        