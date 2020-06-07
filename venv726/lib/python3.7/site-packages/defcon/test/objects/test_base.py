import unittest
import weakref
from defcon.objects.base import BaseObject, BaseDictObject
from defcon.tools.notifications import NotificationCenter
from defcon.test.testTools import NotificationTestObserver


class TestBaseObject(BaseObject):

    def __init__(self):
        super(BaseObject, self).__init__()
        self.name = "TestBaseObject"
        self._dispatcher = None
        self.representationFactories = dict()


class BaseObjectTest(unittest.TestCase):

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_dispatcher(self):
        notificationCenter = NotificationCenter()
        obj = BaseObject()
        obj._dispatcher = weakref.ref(notificationCenter)
        self.assertEqual(obj.dispatcher, notificationCenter)

    def test_addObserver(self):
        obj = BaseObject()
        notificationObject = NotificationTestObserver()
        notificationCenter = NotificationCenter()
        obj._dispatcher = weakref.ref(notificationCenter)
        obj.addObserver(observer=notificationObject,
                        methodName="notificationCallback",
                        notification="BaseObject.Changed")
        self.assertTrue(
            obj.dispatcher.hasObserver(observer=notificationObject,
                                       notification="BaseObject.Changed",
                                       observable=obj)
        )

    def test_removeObserver(self):
        obj = BaseObject()
        notificationObject = NotificationTestObserver()
        notificationCenter = NotificationCenter()
        obj._dispatcher = weakref.ref(notificationCenter)
        obj.dispatcher.addObserver(observer=notificationObject,
                                   methodName="notificationCallback",
                                   notification="BaseObject.Changed",
                                   observable=obj)
        obj.removeObserver(observer=notificationObject,
                           notification="BaseObject.Changed")
        self.assertFalse(
            obj.dispatcher.hasObserver(observer=notificationObject,
                                       notification="BaseObject.Changed",
                                       observable=obj)
        )

    def test_hasObserver(self):
        obj = BaseObject()
        notificationObject = NotificationTestObserver()
        notificationCenter = NotificationCenter()
        obj._dispatcher = weakref.ref(notificationCenter)
        obj.dispatcher.addObserver(observer=notificationObject,
                                   methodName="notificationCallback",
                                   notification="BaseObject.Changed",
                                   observable=obj)
        self.assertTrue(
            obj.hasObserver(observer=notificationObject,
                            notification="BaseObject.Changed")
        )

    def test_dirty_set(self):
        notificationObject = NotificationTestObserver()
        obj = TestBaseObject()
        notificationCenter = NotificationCenter()
        obj._dispatcher = weakref.ref(notificationCenter)
        obj.beginSelfNotificationObservation()
        obj.addObserver(notificationObject, "notificationCallback",
                        "BaseObject.Changed")
        obj.dirty = True
        self.assertEqual(len(notificationObject.stack), 1)
        self.assertEqual(notificationObject.stack[-1],
                         ("BaseObject.Changed", "TestBaseObject"))
        self.assertTrue(obj.dirty)
        obj.dirty = False
        self.assertEqual(notificationObject.stack[-1],
                         ("BaseObject.Changed", "TestBaseObject"))

    def test_dirty_get(self):
        obj = TestBaseObject()
        obj.dirty = True
        self.assertTrue(obj.dirty)
        obj.dirty = False
        self.assertFalse(obj.dirty)


def _representationTestFactory(obj, **kwargs):
    return repr(tuple(sorted(kwargs.items())))


def sortRepresentationKeys(reprensentationKeys):
    return [
        (k, sorted((kk, vv) for kk, vv in v.items()))
        for k, v in sorted(reprensentationKeys,
                           key=lambda t: (t[0], sorted(t[1].keys())))]


class RepresentationsTest(unittest.TestCase):

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

    def setUp(self):
        self.obj = BaseObject()

    def tearDown(self):
        del self.obj

    def test_object_representations(self):
        notificationCenter = NotificationCenter()
        self.obj._dispatcher = weakref.ref(notificationCenter)
        self.obj.representationFactories = dict(
            test=dict(
                factory=_representationTestFactory,
                destructiveNotifications=["BaseObject.Changed"]))
        self.assertEqual(self.obj.getRepresentation("test"), "()")
        self.assertEqual(
            self.obj.representationKeys(),
            [('test', {})]
        )
        self.assertEqual(
            self.obj.getRepresentation("test", attr1="foo",
                                       attr2="bar", attr3=1),
            "(('attr1', 'foo'), ('attr2', 'bar'), ('attr3', 1))"
        )
        self.assertEqual(sortRepresentationKeys(self.obj.representationKeys()),
                         sorted([('test', []),
                                 ('test', [('attr1', 'foo'), ('attr2', 'bar'),
                                           ('attr3', 1)])]))
        self.assertTrue(self.obj.hasCachedRepresentation("test"))
        self.assertTrue(self.obj.hasCachedRepresentation("test", attr1="foo",
                                                         attr2="bar", attr3=1))
        self.assertFalse(self.obj.hasCachedRepresentation("test",
                                                          attr1="not foo",
                                                          attr2="bar",
                                                          attr3=1))
        self.obj.destroyAllRepresentations()
        self.assertEqual(self.obj.representationKeys(),
                         [])
        self.obj.representationFactories["foo"] = dict(
            factory=_representationTestFactory,
            destructiveNotifications=["BaseObject.Changed"]
        )
        self.assertEqual(self.obj.getRepresentation("test"),
                         '()')
        self.assertEqual(self.obj.getRepresentation("test", attr1="foo",
                                                    attr2="bar", attr3=1),
                         "(('attr1', 'foo'), ('attr2', 'bar'), ('attr3', 1))")
        self.assertEqual(
            self.obj.getRepresentation("test", attr21="foo",
                                       attr22="bar", attr23=1),
            "(('attr21', 'foo'), ('attr22', 'bar'), ('attr23', 1))")
        self.assertEqual(self.obj.getRepresentation("foo"),
                         "()")
        self.obj.destroyRepresentation("test", attr21="foo",
                                       attr22="bar", attr23=1)
        self.assertEqual(sortRepresentationKeys(self.obj.representationKeys()),
                         [('foo', []),
                          ('test', []),
                          ('test', [('attr1', 'foo'), ('attr2', 'bar'),
                                    ('attr3', 1)])])
        self.obj.destroyRepresentation("test")
        self.assertEqual(self.obj.representationKeys(),
                         [('foo', {})])

    def test_object_representations_no_dispatcher(self):
        self.obj.representationFactories = dict(
            test=dict(
                factory=_representationTestFactory,
                destructiveNotifications=["BaseObject.Changed"]))
        self.assertEqual(self.obj.getRepresentation("test"), "()")
        self.assertEqual(
            [],
            []
        )

class TestBaseDictObject(BaseDictObject):

    def __init__(self):
        super(BaseDictObject, self).__init__()
        self.name = "TestBaseDictObject"
        self._dispatcher = None
        self.representationFactories = dict()


class BaseDictObjectTest(unittest.TestCase):

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

    def setUp(self):
        self.obj = BaseDictObject()

    def tearDown(self):
        pass

    def test_object_contains(self):
        self.obj["A"] = 1
        self.assertTrue("A" in self.obj)
        self.assertFalse("B" in self.obj)

    def test_len(self):
        self.assertEqual(len(self.obj), 0)
        self.obj["A"] = 1
        self.assertEqual(len(self.obj), 1)

    def test_getItem(self):
        self.obj["A"] = 1
        self.assertEqual(self.obj["A"], 1)

    def test_setItem(self):
        self.obj["A"] = 1
        self.assertEqual(self.obj["A"], 1)
        self.assertTrue(self.obj.dirty)

    def test_delItem(self):
        self.obj["A"] = 1
        self.obj.dirty = False
        del self.obj["A"]
        self.assertFalse("A" in self.obj)
        self.assertTrue(self.obj.dirty)

    def test_get(self):
        self.obj["A"] = 1
        self.assertEqual(self.obj.get("A"), 1)
        self.assertEqual(self.obj.get("B"), None)

    def test_clear(self):
        self.obj["A"] = 1
        self.obj.dirty = False
        self.obj.clear()
        self.assertEqual(len(self.obj), 0)
        self.assertTrue(self.obj.dirty, True)

    def test_update(self):
        self.obj["A"] = 1
        self.obj.dirty = False
        self.obj.update(dict(A=2, B=3))
        self.assertEqual(len(self.obj), 2)
        self.assertEqual(self.obj["A"], 2)
        self.assertEqual(self.obj["B"], 3)
        self.assertEqual(self.obj.dirty, True)

    def test_keys(self):
        self.obj["A"] = 1
        self.assertEqual(list(self.obj.keys()), ["A"])

    def test_values(self):
        self.obj["A"] = 1
        self.assertEqual(list(self.obj.values()), [1])

    def test_items(self):
        self.obj["A"] = 1
        self.assertEqual(list(self.obj.items()), [("A", 1)])

    def test_dirty(self):
        self.assertFalse(self.obj.dirty)
        notdirty = not self.obj.dirty
        self.obj.dirty = notdirty
        self.assertEqual(self.obj.dirty, notdirty)
        self.obj.dirty = not notdirty
        self.assertNotEqual(self.obj.dirty, notdirty)


if __name__ == "__main__":
    unittest.main()
