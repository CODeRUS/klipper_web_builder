#!/usr/bin/python3 -u
#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-

from aiohttp import web, WSMsgType

import logging
import json
import os

from kconfiglib import Kconfig, \
                       Symbol, MENU, COMMENT, \
                       BOOL, TRISTATE, STRING, INT, HEX, UNKNOWN, \
                       expr_value, \
                       TRI_TO_STR


def indent_print(s, indent):
    print(indent*" " + s)


def get_option_value(sc):

    item = {}

    if sc.type == STRING:
      item['type'] = 'str'
    elif sc.type == INT:
      item['type'] = 'int'
    elif sc.type == HEX:
      item['type'] = 'hex'

    item['value'] = sc.str_value

    if isinstance(sc, Symbol) and sc.choice and sc.visibility == 2:
        item['selected'] = sc.choice.selection is sc
        return item

    tri_val_str = (" ", "M", "*")[sc.tri_value]

    if len(sc.assignable) == 1:
      item['assignable'] = True
      item['value'] = tri_val_str
      return item

    if sc.type == BOOL:
      item['type'] = 'bool'
      item['value'] = sc.tri_value == 2
      return item

    if sc.type == TRISTATE:
      item['type'] = 'tristate'
      item['assignable'] = sc.assignable == (1, 2)
      item['value'] = sc.tri_value

    return item


def get_node_value(node):
    item = {}

    if not node.prompt:
        return item

    prompt, prompt_cond = node.prompt
    if not expr_value(prompt_cond):
        return item

    if node.item == MENU:
      item['type'] = 'menu'
      item['text'] = prompt
      return item

    if node.item == COMMENT:
      item['type'] = 'comment'
      item['text'] = prompt
      return item

    sc = node.item

    if sc.type == UNKNOWN:
        return item

    item['text'] = prompt
    item.update(get_option_value(sc))

    if sc.name is not None:
      item['name'] = sc.name

    return item


def parse_menuconfig(node, indent):
    nodes = []
    while node:
      item = get_node_value(node)
      if not item:
        node = node.next
        continue

      if node.list:
        options = parse_menuconfig(node.list, indent + 8)
        item['options'] = options

      nodes += [item]
      node = node.next

    return nodes


def get_menuconfig_noded(kconf):
    data = {'title': kconf.mainmenu_text}

    nodes = parse_menuconfig(kconf.top_node.list, 0)
    data['options'] = nodes
    return data


async def handle_post(request):
  data = await request.post()
  print(data)

  kconf = request.app['kconf']
  config_filename = request.app['config_filename']
  kconf.write_config(config_filename)

  return web.FileResponse("index.html", chunk_size=256 * 1024)


async def handle_ws(request):
  ws = web.WebSocketResponse()
  await ws.prepare(request)

  async for msg in ws:
    if msg.type == WSMsgType.TEXT:
      print(msg.data)

      if msg.data == 'close':
        await ws.close()
        return ws

      kconf = request.app['kconf']

      if msg.data == 'init':
        pass
      else:
        command = json.loads(msg.data)
        if 'option' in command:
          cmd = command['option']
          if cmd in kconf.syms or cmd in kconf.named_choices:
            kconf.syms[cmd].set_value('y')

        else:
          for key in command:
            if key in kconf.syms or key in kconf.named_choices:
              kconf.syms[key].set_value(command[key])

      data = get_menuconfig_noded(kconf)
      await ws.send_str(json.dumps(data))
    elif msg.type == WSMsgType.ERROR:
      print('ws connection closed with exception %s' %
            ws.exception())

  print('websocket connection closed')

  return ws


async def handle_index(request: web.Request) -> web.StreamResponse:
  return web.FileResponse("index.html", chunk_size=256 * 1024)


def run(klipper_folder, kconfig, port=7055):
  logging.basicConfig(level=logging.INFO)

  app = web.Application()
  app.add_routes(
    [
      web.get("/", handle_index),
      web.get("//", handle_index),
      web.post("/", handle_post),
      web.post("//", handle_post),
      web.get("/ws", handle_ws),
      web.get("//ws", handle_ws),
    ]
  )

  kconf = Kconfig(kconfig)
  config_filename = os.path.join(klipper_folder, '.config')

  if os.path.exists(config_filename):
    try:
      print(kconf.load_config(config_filename))
    except EnvironmentError as e:
      print(e, file=sys.stderr)

  app['kconf'] = kconf
  app['config_filename'] = config_filename

  web.run_app(app, port=port)
  logging.info('Stopping http server...\n')


if __name__ == '__main__':
  from sys import argv

  if len(argv) == 1:
    print('No klipper folder argument found!')
    exit()

  klipper_folder = argv[1]
  kconfig = os.path.join(klipper_folder, 'src/Kconfig')
  if not os.path.exists(kconfig):
    print('Can\'t open Kconfig file')
    exit()

  os.environ['srctree'] = klipper_folder

  try:
    if len(argv) == 3:
      run(klipper_folder, kconfig, port=int(argv[2]))
    else:
      run(klipper_folder, kconfig)
  except KeyboardInterrupt:
    pass
