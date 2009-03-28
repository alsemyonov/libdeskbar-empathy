# -*- coding: UTF-8 -*-
import deskbar.core.Utils
import deskbar.interfaces.Action
import deskbar.interfaces.Match
import deskbar.interfaces.Module
import logging
import dbus
import dbus.mainloop.glib
import re
import traceback

from deskbar.handlers.actions.CopyToClipboardAction import CopyToClipboardAction

dbus.mainloop.glib.DBusGMainLoop(set_as_default = True)

HANDLERS = ['EmpathyHandler']

class EmpathyHandler(deskbar.interfaces.Module):
  INFOS = {'icon': deskbar.core.Utils.load_icon('empathy'),
      'name': 'Empathy IM integration',
      'description': 'Search Empathy contacts',
      'version': '0.0.1'
      }

  def __init__(self):
    deskbar.interfaces.Module.__init__(self)
    self._bus = dbus.SessionBus()
    self._connections = []
    self._contacts = {}

  def query(self, text):
    logging.debug("lookup contacts")
    contacts = self.get_contacts()
    logging.debug("Searching for «%s»" % (text, ))
    reg = re.compile(text, re.I | re.U)
    logging.debug(reg)
    for name in contacts:
      if reg.match(name):
        logging.debug(name)
        self._emit_query_ready(name, [EmpathyContactMatch(contacts[name])])
  
  def get_connections(self, refresh=False):
    """Getting all active connections"""

    if refresh or len(self._connections) == 0:
      logging.debug("Retrieving connections")
      proxy = self._bus.get_object('org.freedesktop.Telepathy.MissionControl',
          '/org/freedesktop/Telepathy/MissionControl')
      connections = proxy.GetOnlineConnections()
      for connection in connections:
        (bus_name, object_path) = proxy.GetConnection(connection)
        connection = self._bus.get_object(bus_name, object_path)
        self._connections.append(connection)
    return self._connections

  def get_contacts(self, refresh=False):
    """Getting all contacts from contact-lists"""

    if refresh or len(self._contacts) == 0:
      logging.debug("Retrieving contacts")
      for connection in self.get_connections():
        if connection.GetProtocol() in ('jabber', 'icq', 'local_xmpp'):
          channels_info = connection.ListChannels()
          for channel_info in channels_info:
            logging.debug(channel_info[0])
            channel = self._bus.get_object(connection.bus_name, 
                channel_info[0], 
                channel_info[1])
            try:
              members = channel.GetMembers()
              if len(members) > 0:
                aliases = connection.GetAliases(members)
                for id in aliases:
                  name = aliases[id]
                  if not self._contacts.has_key(name):
                    self._contacts[name] = TelepathyContact(connection, id, name)
            except dbus.DBusException:
              pass
    return self._contacts

class TelepathyContact:
  def __init__(self, connection, id, name):
    self._connection = connection
    self._id = id
    self._name = name

  def get_name(self):
    return self._name

  def open_chat(self):
    self._connection.RequestChannel(
        dbus.String('org.freedesktop.Telepathy.Channel.Type.Text'), dbus.Int32(1), # Text chat
        self._id,
        dbus.Boolean(True),
        dbus_interface = 'org.freedesktop.Telepathy.Connection'
      )
    logging.debug("Opening chat with %s" % (self._name, ))

  def __unicode__(self):
    return self._name

class EmpathyContactMatch(deskbar.interfaces.Match):
  def __init__(self, contact, **kwargs):
    deskbar.interfaces.Match.__init__(self,
        name=contact.get_name(), 
        icon='empathy', 
        category='people', 
        **kwargs)

    self._contact = contact
    self._name = contact.get_name()
    self.add_action(ChatAction(self))
    self.add_action(CopyToClipboardAction("URL", self))

  def get_hash(self):
    return self._name

class ChatAction(deskbar.interfaces.Action):

  def __init__(self, contact):
    deskbar.interfaces.Action.__init__(self, contact.get_name())
    self._contact = contact
  
  def activate(self, text=None):
    contact.open_chat()
  
  def get_verb(self):
    return 'Chat with %(name)s'

  def get_icon(self):
    return 'empathy'

# class EmpathyOpenConf(deskbar.interfaces.Action):
#   pass
# 
# class EmpathySearchLog(deskbar.interfaces.Action):
#   pass
