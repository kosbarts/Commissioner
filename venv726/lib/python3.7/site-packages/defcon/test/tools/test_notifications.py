import unittest
from defcon.tools.notifications import NotificationCenter
from defcon.test.testTools import NotificationTestObserver


class _TestObservable(object):

    def __init__(self, center, name):
        self.center = center
        self.name = name

    def postNotification(self, name):
        self.center.postNotification(name, self)


class NotificationCenterTest(unittest.TestCase):

    def __init__(self, methodName):
        unittest.TestCase.__init__(self, methodName)

    def test_addObserver_notification_observable(self):
        center = NotificationCenter()
        observable = _TestObservable(center, "Observable")
        observer = NotificationTestObserver()
        center.addObserver(observer, "notificationCallback", "A", observable)
        self.assertTrue(center.hasObserver(observer, "A", observable))
        self.assertFalse(center.hasObserver(observer, "B", observable))

    def test_addObserver_notification_no_observable(self):
        center = NotificationCenter()
        observable = _TestObservable(center, "Observable")
        observer = NotificationTestObserver()
        center.addObserver(observer, "notificationCallback", "A", None)
        self.assertTrue(center.hasObserver(observer, "A", None))
        self.assertFalse(center.hasObserver(observer, "A", observable))

    def test_addObserver_no_notification_observable(self):
        center = NotificationCenter()
        observable = _TestObservable(center, "Observable")
        observer = NotificationTestObserver()
        center.addObserver(observer, "notificationCallback", None, observable)
        self.assertTrue(center.hasObserver(observer, None, observable))
        self.assertFalse(center.hasObserver(observer, "A", observable))

    def test_addObserver_no_notification_no_observable(self):
        center = NotificationCenter()
        observable = _TestObservable(center, "Observable")
        observer = NotificationTestObserver()
        center.addObserver(observer, "notificationCallback", None, None)
        self.assertTrue(center.hasObserver(observer, None, None))
        self.assertFalse(center.hasObserver(observer, "A", observable))
        self.assertFalse(center.hasObserver(observer, None, observable))
        self.assertFalse(center.hasObserver(observer, "A", None))

    def test_removeObserver(self):
        center = NotificationCenter()
        observable = _TestObservable(center, "Observable")
        observer = NotificationTestObserver()
        center.addObserver(observer, "notificationCallback", "A", observable)
        center.removeObserver(observer, "A", observable)
        self.assertFalse(center.hasObserver(observer, "A", observable))

    def test_removeObserver_notification_observable(self):
        center = NotificationCenter()
        observable = _TestObservable(center, "Observable")
        observer = NotificationTestObserver()
        center.addObserver(observer, "notificationCallback", "A", observable)
        center.removeObserver(observer, "A", observable)
        self.assertFalse(center.hasObserver(observer, "A", observable))

    def test_removeObserver_notification_no_observable(self):
        center = NotificationCenter()
        _TestObservable(center, "Observable")
        observer = NotificationTestObserver()
        center.addObserver(observer, "notificationCallback", "A", None)
        center.removeObserver(observer, "A", None)
        self.assertFalse(center.hasObserver(observer, "A", None))

    def test_removeObserver_no_notification_observable(self):
        center = NotificationCenter()
        observable = _TestObservable(center, "Observable")
        observer = NotificationTestObserver()
        center.addObserver(observer, "notificationCallback", None, observable)
        center.removeObserver(observer, None, observable)
        self.assertFalse(center.hasObserver(observer, None, observable))

    def test_removeObserver_no_notification_no_observable(self):
        center = NotificationCenter()
        _TestObservable(center, "Observable")
        observer = NotificationTestObserver()
        center.addObserver(observer, "notificationCallback", None, None)
        center.removeObserver(observer, None, None)
        self.assertFalse(center.hasObserver(observer, None, None))

    def test_postNotification_notification_observable(self):
        # notification, observable
        center = NotificationCenter()
        observable1 = _TestObservable(center, "Observable1")
        observable2 = _TestObservable(center, "Observable2")
        observer = NotificationTestObserver()
        center.addObserver(observer, "notificationCallback", "A", observable1)
        center.postNotification("A", observable1)
        self.assertEqual(observer.stack[-1], ("A", "Observable1"))
        center.postNotification("A", observable2)
        self.assertEqual(observer.stack[-1], ("A", "Observable1"))
        center.postNotification("B", observable1)
        self.assertEqual(observer.stack[-1], ("A", "Observable1"))
        center.postNotification("B", observable2)
        self.assertEqual(observer.stack[-1], ("A", "Observable1"))

    def test_postNotification_notification_no_observable(self):
        # notification, no observable
        center = NotificationCenter()
        observable1 = _TestObservable(center, "Observable1")
        observable2 = _TestObservable(center, "Observable2")
        observer = NotificationTestObserver()
        center.addObserver(observer, "notificationCallback", "A", None)
        center.postNotification("A", observable1)
        self.assertEqual(observer.stack[-1], ("A", "Observable1"))
        center.postNotification("A", observable2)
        self.assertEqual(observer.stack[-1], ("A", "Observable2"))
        center.postNotification("B", observable1)
        self.assertEqual(observer.stack[-1], ("A", "Observable2"))
        center.postNotification("B", observable2)
        self.assertEqual(observer.stack[-1], ("A", "Observable2"))


    def test_postNotification_no_notification_observable(self):
        # no notification, observable
        center = NotificationCenter()
        observable1 = _TestObservable(center, "Observable1")
        observable2 = _TestObservable(center, "Observable2")
        observer = NotificationTestObserver()
        center.addObserver(observer, "notificationCallback", None, observable1)
        center.postNotification("A", observable1)
        self.assertEqual(observer.stack[-1], ("A", "Observable1"))
        center.postNotification("A", observable2)
        center.postNotification("B", observable1)
        self.assertEqual(observer.stack[-1], ("B", "Observable1"))
        center.postNotification("B", observable2)


    def test_postNotification_no_notification_no_observable(self):
        # no notification, no observable
        center = NotificationCenter()
        observable1 = _TestObservable(center, "Observable1")
        observable2 = _TestObservable(center, "Observable2")
        observer = NotificationTestObserver()
        center.addObserver(observer, "notificationCallback", None, None)
        center.postNotification("A", observable1)
        self.assertEqual(observer.stack[-1], ("A", "Observable1"))
        center.postNotification("A", observable2)
        self.assertEqual(observer.stack[-1], ("A", "Observable2"))
        center.postNotification("B", observable1)
        self.assertEqual(observer.stack[-1], ("B", "Observable1"))
        center.postNotification("B", observable2)
        self.assertEqual(observer.stack[-1], ("B", "Observable2"))

    def test_hold_and_releaseHeldNotifications_all_notifications(self):
        "Hold all notifications"
        center = NotificationCenter()
        observable1 = _TestObservable(center, "Observable1")
        observable2 = _TestObservable(center, "Observable2")
        observer = NotificationTestObserver()
        center.addObserver(observer, "notificationCallback", "A", observable1)
        center.addObserver(observer, "notificationCallback", "B", observable1)
        center.addObserver(observer, "notificationCallback", "C", observable2)

        center.holdNotifications()
        observable1.postNotification("A")
        self.assertEqual(len(observer.stack), 0)
        observable1.postNotification("A")
        self.assertEqual(len(observer.stack), 0)
        observable1.postNotification("B")
        self.assertEqual(len(observer.stack), 0)
        observable2.postNotification("C")
        self.assertEqual(len(observer.stack), 0)
        center.releaseHeldNotifications()
        self.assertEqual(observer.stack[-3], ("A", "Observable1"))
        self.assertEqual(observer.stack[-2], ("B", "Observable1"))
        self.assertEqual(observer.stack[-1], ("C", "Observable2"))
        self.assertEqual(len(observer.stack), 3)

    def test_hold_and_releaseHeldNotifications_notifications_of_observable(self):
        "Hold all notifications of a specific observable"
        center = NotificationCenter()
        observable1 = _TestObservable(center, "Observable1")
        observable2 = _TestObservable(center, "Observable2")
        observer = NotificationTestObserver()
        center.addObserver(observer, "notificationCallback", "A", observable1)
        center.addObserver(observer, "notificationCallback", "B", observable1)
        center.addObserver(observer, "notificationCallback", "C", observable2)

        center.holdNotifications(observable=observable1)
        observable1.postNotification("A")
        observable1.postNotification("A")
        observable1.postNotification("B")
        observable2.postNotification("C")
        self.assertEqual(observer.stack[-1], ("C", "Observable2"))
        center.releaseHeldNotifications(observable=observable1)
        self.assertEqual(observer.stack[-2], ("A", "Observable1"))
        self.assertEqual(observer.stack[-1], ("B", "Observable1"))
        self.assertEqual(len(observer.stack), 3)

    def test_hold_and_releaseHeldNotifications_notifications_of_observable(
            self):
        "Hold all notifications of a specific notification"
        center = NotificationCenter()
        observable1 = _TestObservable(center, "Observable1")
        observable2 = _TestObservable(center, "Observable2")
        observer = NotificationTestObserver()
        center.addObserver(observer, "notificationCallback", "A", observable1)
        center.addObserver(observer, "notificationCallback", "B", observable1)
        center.addObserver(observer, "notificationCallback", "C", observable2)

        center.holdNotifications(notification="A")
        observable1.postNotification("A")
        observable1.postNotification("A")
        observable1.postNotification("B")
        self.assertEqual(observer.stack[-1], ("B", "Observable1"))
        observable2.postNotification("C")
        self.assertEqual(observer.stack[-1], ("C", "Observable2"))
        center.releaseHeldNotifications(notification="A")
        self.assertEqual(observer.stack[-1], ("A", "Observable1"))
        self.assertEqual(len(observer.stack), 3)

    def test_areNotificationsHeld_all_held(self):
        center = NotificationCenter()
        observable = _TestObservable(center, "Observable")
        observer = NotificationTestObserver()
        center.addObserver(observer, "notificationCallback", "A", observable)
        center.holdNotifications()
        self.assertTrue(center.areNotificationsHeld())
        center.releaseHeldNotifications()
        self.assertFalse(center.areNotificationsHeld())

    def test_areNotificationsHeld_observable_off(self):
        center = NotificationCenter()
        observable1 = _TestObservable(center, "Observable1")
        observable2 = _TestObservable(center, "Observable2")
        observer = NotificationTestObserver()
        center.addObserver(observer, "notificationCallback", "A", observable1)
        center.addObserver(observer, "notificationCallback", "B", observable2)
        center.holdNotifications(observable=observable1)
        self.assertTrue(center.areNotificationsHeld(observable=observable1))
        self.assertFalse(center.areNotificationsHeld(observable=observable2))
        center.releaseHeldNotifications(observable=observable1)
        self.assertFalse(center.areNotificationsHeld(observable=observable1))

    def test_areNotificationsHeld_notification_off(self):
        center = NotificationCenter()
        observable = _TestObservable(center, "Observable")
        observer = NotificationTestObserver()
        center.addObserver(observer, "notificationCallback", "A", observable)
        center.addObserver(observer, "notificationCallback", "B", observable)
        center.holdNotifications(notification="A")
        self.assertTrue(center.areNotificationsHeld(notification="A"))
        self.assertFalse(center.areNotificationsHeld(notification="B"))
        center.releaseHeldNotifications(notification="A")
        self.assertFalse(center.areNotificationsHeld(notification="A"))

    def test_areNotificationsHeld_observer_off(self):
        center = NotificationCenter()
        observable = _TestObservable(center, "Observable")
        observer1 = NotificationTestObserver()
        observer2 = NotificationTestObserver()
        center.addObserver(observer1, "notificationCallback", "A", observable)
        center.addObserver(observer2, "notificationCallback", "A", observable)
        center.holdNotifications(observer=observer1)
        self.assertTrue(center.areNotificationsHeld(observer=observer1))
        self.assertFalse(center.areNotificationsHeld(observer=observer2))
        center.releaseHeldNotifications(observer=observer1)
        self.assertFalse(center.areNotificationsHeld(observer=observer1))

    def test_disable_enableNotifications_all_notifications(self):
        # disable all notifications
        center = NotificationCenter()
        observable1 = _TestObservable(center, "Observable1")
        observable2 = _TestObservable(center, "Observable2")
        observer = NotificationTestObserver()
        center.addObserver(observer, "notificationCallback", "A", observable1)
        center.addObserver(observer, "notificationCallback", "B", observable1)
        center.addObserver(observer, "notificationCallback", "C", observable2)
        center.disableNotifications()
        observable1.postNotification("A")
        observable1.postNotification("B")
        observable2.postNotification("C")
        center.enableNotifications()
        observable1.postNotification("A")
        self.assertEqual(observer.stack[-1], ("A", "Observable1"))

    def test_disable_enableNotifications_specific_observable(self):
        # disable all notifications for a specific observable
        center = NotificationCenter()
        observable1 = _TestObservable(center, "Observable1")
        observable2 = _TestObservable(center, "Observable2")
        observer = NotificationTestObserver()
        center.addObserver(observer, "notificationCallback", "A", observable1)
        center.addObserver(observer, "notificationCallback", "B", observable1)
        center.addObserver(observer, "notificationCallback", "C", observable2)
        center.disableNotifications(observable=observable1)
        observable1.postNotification("A")
        observable1.postNotification("B")
        observable2.postNotification("C")
        self.assertEqual(observer.stack[-1], ("C", "Observable2"))
        center.enableNotifications(observable=observable1)
        observable1.postNotification("A")
        self.assertEqual(observer.stack[-1], ("A", "Observable1"))

    def test_disable_enableNotifications_specific_notification(self):
        # disable all notifications for a specific notification
        center = NotificationCenter()
        observable1 = _TestObservable(center, "Observable1")
        observable2 = _TestObservable(center, "Observable2")
        observer = NotificationTestObserver()
        center.addObserver(observer, "notificationCallback", "A", observable1)
        center.addObserver(observer, "notificationCallback", "B", observable1)
        center.addObserver(observer, "notificationCallback", "C", observable2)
        center.disableNotifications(notification="A")
        observable1.postNotification("A")
        observable1.postNotification("B")
        self.assertEqual(observer.stack[-1], ("B", "Observable1"))
        observable2.postNotification("C")
        self.assertEqual(observer.stack[-1], ("C", "Observable2"))
        center.enableNotifications(notification="A")
        observable1.postNotification("A")
        self.assertEqual(observer.stack[-1], ("A", "Observable1"))

    def test_disable_enableNotifications_specific_observer(self):
        # disable all notifications for a specific observer
        center = NotificationCenter()
        observable1 = _TestObservable(center, "Observable1")
        observable2 = _TestObservable(center, "Observable2")
        observer = NotificationTestObserver()
        center.addObserver(observer, "notificationCallback", "A", observable1)
        center.addObserver(observer, "notificationCallback", "B", observable1)
        center.addObserver(observer, "notificationCallback", "C", observable2)
        center.disableNotifications(observer=observer)
        observable1.postNotification("A")
        observable1.postNotification("B")
        observable2.postNotification("C")
        center.enableNotifications(observer=observer)
        observable1.postNotification("A")
        self.assertEqual(observer.stack[-1], ("A", "Observable1"))

    def test_areNotificationsDisabled_all_off(self):
        center = NotificationCenter()
        observable1 = _TestObservable(center, "Observable1")
        observable2 = _TestObservable(center, "Observable2")
        observer = NotificationTestObserver()
        center.addObserver(observer, "notificationCallback", "A", observable1)
        center.addObserver(observer, "notificationCallback", "B", observable2)
        center.disableNotifications()
        self.assertTrue(center.areNotificationsDisabled())
        center.enableNotifications()
        self.assertFalse(center.areNotificationsDisabled())

    def test_areNotificationsDisabled_observable_off(self):
        center = NotificationCenter()
        observable1 = _TestObservable(center, "Observable1")
        observable2 = _TestObservable(center, "Observable2")
        observer = NotificationTestObserver()
        center.addObserver(observer, "notificationCallback", "A", observable1)
        center.addObserver(observer, "notificationCallback", "B", observable2)
        center.disableNotifications(observable=observable1)
        self.assertTrue(
            center.areNotificationsDisabled(observable=observable1))
        self.assertFalse(
            center.areNotificationsDisabled(observable=observable2))
        center.enableNotifications(observable=observable1)
        self.assertFalse(
            center.areNotificationsDisabled(observable=observable1))

    def test_areNotificationsDisabled_notification_off(self):
        center = NotificationCenter()
        observable1 = _TestObservable(center, "Observable1")
        observable2 = _TestObservable(center, "Observable2")
        observer = NotificationTestObserver()
        center.addObserver(observer, "notificationCallback", "A", observable1)
        center.addObserver(observer, "notificationCallback", "B", observable2)
        center.disableNotifications(notification="A")
        self.assertTrue(center.areNotificationsDisabled(notification="A"))
        self.assertFalse(center.areNotificationsDisabled(notification="B"))
        center.enableNotifications(notification="A")
        self.assertFalse(center.areNotificationsDisabled(notification="A"))

    def test_areNotificationsDisabled_observer_off(self):
        center = NotificationCenter()
        observable1 = _TestObservable(center, "Observable1")
        observer1 = NotificationTestObserver()
        observer2 = NotificationTestObserver()
        center.addObserver(observer1, "notificationCallback", "A", observable1)
        center.addObserver(observer2, "notificationCallback", "A", observable1)
        center.disableNotifications(observer=observer1)
        self.assertTrue(center.areNotificationsDisabled(observer=observer1))
        self.assertFalse(center.areNotificationsDisabled(observer=observer2))
        center.enableNotifications(observer=observer1)
        self.assertFalse(center.areNotificationsDisabled(observer=observer1))


if __name__ == "__main__":
    unittest.main()
