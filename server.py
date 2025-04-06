#!/usr/bin/python3 -u
#!/usr/bin/python3 -u
# -*- coding: utf-8 -*-

from aiohttp import web, WSMsgType
from subprocess import PIPE, Popen, STDOUT

from logging.handlers import RotatingFileHandler

import sys

import argparse
import logging
import json
import os

from kconfiglib import Kconfig, \
                       Symbol, MENU, COMMENT, \
                       BOOL, TRISTATE, STRING, INT, HEX, UNKNOWN, \
                       expr_value


logging.basicConfig(
    handlers=[logging.StreamHandler(sys.stdout)],
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


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


def get_menuconfig_nodes(kconf):
    data = {'title': kconf.mainmenu_text}

    nodes = parse_menuconfig(kconf.top_node.list, 0)
    data['options'] = nodes
    return data


async def process_submit(ws, app, cmd):
  logger.info(f'processing submit: {cmd}')
  klipper_folder = app['klipper_folder']
  command = 'make'
  if cmd == 'clean':
    command += ' clean'

  with Popen(command, cwd=klipper_folder, shell=True, stdout=PIPE, stderr=STDOUT, bufsize=1) as sp:
    for line in sp.stdout:
      text = line.decode('utf-8')
      if text.strip().startswith('Creating hex file'):
        filename = text.strip().split()[-1]
        app['filename'] = filename
        logger.info(f'got filename: {filename}')
        await ws.send_str(f'{{"file": "{filename}"}}')
      data = {'text': text}
      await ws.send_str(json.dumps(data));

  await ws.send_str('{"text": "process finished"}')
  await ws.send_str('{"text": ""}')


async def handle_ws(request):
  ws = web.WebSocketResponse()
  await ws.prepare(request)

  async for msg in ws:
    if msg.type == WSMsgType.TEXT:
      print(msg.data)

      kconf = request.app['kconf']

      if msg.data == 'init':
        pass

      elif msg.data.startswith('{'):
        kconf = request.app['kconf']
        command = json.loads(msg.data)
        if 'option' in command:
          cmd = command['option']
          if cmd in kconf.syms or cmd in kconf.named_choices:
            kconf.syms[cmd].set_value('y')

        else:
          for key in command:
            if key in kconf.syms or key in kconf.named_choices:
              kconf.syms[key].set_value(command[key])

      else:
        config_filename = request.app['config_filename']
        kconf.write_config(config_filename)
        await process_submit(ws, request.app, msg.data)
        continue

      kconf = request.app['kconf']
      data = get_menuconfig_nodes(kconf)
      await ws.send_str(json.dumps(data))
    elif msg.type == WSMsgType.ERROR:
      logger.warning('ws connection closed with exception %s' %
            ws.exception())

  logger.warning('websocket connection closed')

  return ws


async def handle_index(request: web.Request) -> web.StreamResponse:
  return web.FileResponse("index.html", chunk_size=256 * 1024)


async def handle_download(request: web.Request) -> web.StreamResponse:
  klipper_folder = request.app['klipper_folder']
  filename = request.app['filename']
  file_path = os.path.join(klipper_folder, filename)
  if os.path.exists(file_path):
    response = web.FileResponse(file_path, chunk_size=256 * 1024)
    fname = filename.split('/')[-1]
    response.headers['Content-Disposition'] = f'attachment; filename="{fname}"';
    return response
  else:
    raise web.HTTPNotFound


def run(klipper_folder, kconfig, port=7055):
  app = web.Application()
  app.add_routes(
    [
      web.get("/", handle_index),
      web.get("//", handle_index),
      web.get("/download", handle_download),
      web.get("//download", handle_download),
      web.get("/menuconfig_ws", handle_ws),
      web.get("//menuconfig_ws", handle_ws),
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
  app['klipper_folder'] = klipper_folder

  web.run_app(app, port=port)
  logger.info('Stopping http server...\n')


if __name__ == '__main__':
  parser = argparse.ArgumentParser(description="Moonraker Telegram Bot")
  parser.add_argument(
      "-k",
      "--klipperdir",
      default="~/klipper",
      metavar="<klipperdir>",
      help="Location of klipper directory",
  )
  parser.add_argument(
      "-l",
      "--logfile",
      metavar="<logfile>",
      help="Location of server log file",
  )
  parser.add_argument(
      "-p",
      "--port",
      default=7055,
      type=int,
      metavar="<port>",
      help="Location of server log file",
  )
  system_args = parser.parse_args()

  klipper_folder = system_args.klipperdir
  if len(klipper_folder) == 0 or not os.path.exists(klipper_folder):
    logger.error('klipper folder not found!')
    exit()

  kconfig = os.path.join(klipper_folder, 'src/Kconfig')
  if not os.path.exists(kconfig):
    logger.error('Can\'t open Kconfig file')
    exit()

  rotatingHandler = RotatingFileHandler(
      system_args.logfile,
      maxBytes=26214400,
      backupCount=0,
  )
  rotatingHandler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
  logger.addHandler(rotatingHandler)

  os.environ['srctree'] = klipper_folder

  try:
    run(klipper_folder, kconfig, system_args.port)
  except KeyboardInterrupt:
    pass
