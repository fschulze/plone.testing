"""ZODB-specific helpers and layers 
"""

import os

try:
    from zope.testrunner import runner
except ImportError, exc_value:
    try:
        from zope.testing.testrunner import runner
    except ImportError:
        raise exc_value

from plone.testing import Layer

def stackDemoStorage(db=None, name=None, base=None, changes=None, layer=None):
    """Create a new DemoStorage that has the given database as a base.
    ``db`` may be none, in which case a base demo storage will be created.
    ``name`` is optional, but can be used to name the storage.
    
    The usual pattern in a layer is::
    
        def setUp(self):
            self['zodbDB'] = stackDemoStorage(self.get('zodbDB'), name='mylayer')
        
        def tearDown(self):
            self['zodbDB'].close()
            del self['zodbDB']
    """
    
    from ZODB.DemoStorage import DemoStorage
    from ZODB.DB import DB

    storages = [storage for storage in os.environ.get(
        'PLONE_TESTING_FILESTORAGES', '').split(',') if storage]
    is_db_setup = False
    if layer is not None and changes is None and storages:
        from zope.dottedname import resolve
        gathered = []
        for dotted in storages:
            resolved = resolve.resolve(dotted)
            runner.gather_layers(resolved, gathered)
        if layer in gathered:
            from ZODB import FileStorage
            storages_dir = os.path.join('var', 'filestorage')
            if not os.path.isdir(storages_dir):
                os.makedirs(storages_dir)
            file_name = os.path.join(storages_dir, layer.__name__ + '.fs')
            if os.path.isfile(file_name):
                is_db_setup = True
            changes = FileStorage.FileStorage(file_name)
    
    if base is None:
        if db is not None:
            base = db.storage
        else:
            from ZODB import MappingStorage
            base = MappingStorage.MappingStorage()
    storage = DemoStorage(
        name=name, base=base, changes=changes, close_base_on_close=False)
    
    stacked = DB(storage)
    if is_db_setup:
        stacked.db_setup = is_db_setup
    return stacked

class EmptyZODB(Layer):
    """Set up a new ZODB database using ``DemoStorage``. The database object
    is available as the resource ``zodbDB``.
    
    For each test, a new connection is created, and made available as the
    resource ``zodbConnection``. The ZODB root is available as ``zodbRoot``.
    A new transaction is then begun.
    
    On test tear-down, the transaction is aborted, the connection closed,
    and the two resources deleted.
    
    If you want to build your own layer with ZODB functionality, you may 
    want to subclass this class and override one or both of
    ``createStorage()`` and ``createDatabase()``.
    """
    
    defaultBases = ()
    
    def setUp(self):
        self['zodbDB'] = self.createDatabase(self.createStorage())
        
    def tearDown(self):
        self['zodbDB'].close()
        del self['zodbDB']
    
    def testSetUp(self):
        self['zodbConnection'] = connection = self['zodbDB'].open()
        self['zodbRoot']       = connection.root()
        
        import transaction
        transaction.begin()
    
    def testTearDown(self):
        import transaction
        transaction.abort()
        
        self['zodbConnection'].close()
        
        del self['zodbConnection']
        del self['zodbRoot']
    
    # Template methods for use in subclasses, if required
    
    def createStorage(self):
        """Create a new storage.
        
        You may want to subclass this class when creating a custom layer. You
        can then override this method to create a different storage. The
        default is an empty DemoStorage.
        """
        
        from ZODB.DemoStorage import DemoStorage
        return DemoStorage(name='EmptyZODB')
    
    def createDatabase(self, storage):
        """Create a new database from the given storage.
        
        Like ``createStorage()``, this hook exists for subclasses to override
        as necessary.
        """
        
        from ZODB.DB import DB
        return DB(storage)
    
EMPTY_ZODB = EmptyZODB()
