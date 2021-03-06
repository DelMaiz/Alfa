# -*- coding: utf-8 -*-
# -*- Channel Goovie -*-
# -*- Created for Alfa-addon -*-
# -*- By the Alfa Develop Group -*-

import re
import urllib
from channelselector import get_thumb
from core import httptools
from core import jsontools
from core import scrapertools
from core import servertools
from core import tmdb
from core.item import Item
from channels import filtertools
from channels import autoplay
from platformcode import config, logger


IDIOMAS = {'EspaL':'Cast', 'LatinoL':'Lat', 'SubL':'VOSE', 'OriL':'VO'}
list_language = IDIOMAS.values()

CALIDADES = {'1080p':'1080','720p':'720','480p':'480','360p':'360'}

list_quality = ['1080', '720', '480', '360']

list_servers = [
    'powvideo'
]

__comprueba_enlaces__ = config.get_setting('comprueba_enlaces', 'goovie')
__comprueba_enlaces_num__ = config.get_setting('comprueba_enlaces_num', 'goovie')

host = 'https://goovie.co/'

def mainlist(item):
    logger.info()

    autoplay.init(item.channel, list_servers, list_quality)

    itemlist = []

    itemlist.append(Item(channel=item.channel, title='Peliculas', action='sub_menu', type='peliculas',
                         thumbnail= get_thumb('movies', auto=True)))
    itemlist.append(Item(channel=item.channel, title='Series', action='sub_menu', type='series',
                         thumbnail= get_thumb('tvshows', auto=True)))
    itemlist.append(Item(channel=item.channel, title='Colecciones', action='list_collections',
                        url= host+'listas=populares', thumbnail=get_thumb('colections', auto=True)))
    itemlist.append(
        item.clone(title="Buscar", action="search", url=host + 'search?go=', thumbnail=get_thumb("search", auto=True),
                   extra='movie'))

    autoplay.show_option(item.channel, itemlist)

    return itemlist

def sub_menu(item):
    logger.info()

    itemlist=[]

    itemlist.append(Item(channel=item.channel, title='Todas', url=host + item.type, action='list_all',
                         thumbnail=get_thumb('all', auto=True), type=item.type))
    itemlist.append(Item(channel=item.channel, title='Genero', action='section',
                         thumbnail=get_thumb('genres', auto=True), type=item.type))
    itemlist.append(Item(channel=item.channel, title='Por Año', action='section',
                         thumbnail=get_thumb('year', auto=True), type=item.type))

    return itemlist

def get_source(url, referer=None):
    logger.info()
    if referer is None:
        data = httptools.downloadpage(url).data
    else:
        data = httptools.downloadpage(url, headers={'Referer':referer}).data
    data = re.sub(r'\n|\r|\t|&nbsp;|<br>|\s{2,}', "", data)
    return data


def get_language(lang_data):
    logger.info()
    language = []

    lang_list = scrapertools.find_multiple_matches(lang_data, '/flags/(.*?).png\)')
    for lang in lang_list:
        if lang == 'en':
            lang = 'vose'
        if lang not in language:
            language.append(lang)
    return language

def section(item):
    logger.info()
    itemlist=[]
    data = get_source(host+item.type)
    if 'Genero' in item.title:
        data = scrapertools.find_single_match(data, 'Generos.*?</ul>')
    elif 'Año' in item.title:
        data = scrapertools.find_single_match(data, 'Años.*?</ul>')
    patron = '<li onclick="filter\(this, \'([^\']+)\', \d+\);">'
    matches = re.compile(patron, re.DOTALL).findall(data)

    for scrapedtitle in matches:
        title = scrapedtitle
        if r'\d+' in scrapedtitle:
            url = '%s%s/filtro/,/%s,' % (host, item.type, title)
        else:
            url = '%s%s/filtro/%s,/,' % (host, item.type, title)
        itemlist.append(Item(channel=item.channel, url=url, title=title, action='list_all',
                                 type=item.type))
    return itemlist


def list_all(item):
    logger.info()
    itemlist = []

    data = get_source(item.url)
    patron = '<article class="Item"><a href="([^>]+)"><div class="Poster"><img src="([^"]+)".*?'
    patron += '<h2>([^>]+)</h2>.*?</article>'
    matches = re.compile(patron, re.DOTALL).findall(data)

    for scrapedurl, scrapedthumbnail, scrapedtitle in matches:

        title = scrapedtitle
        thumbnail = scrapedthumbnail.strip()
        url = scrapedurl
        filter_thumb = thumbnail.replace("https://image.tmdb.org/t/p/w154", "")
        filter_list = {"poster_path": filter_thumb}
        filter_list = filter_list.items()
        new_item = Item(channel=item.channel,
                        title=title,
                        url=url,
                        thumbnail=thumbnail,
                        infoLabels={'filtro':filter_list})

        if item.type == 'peliculas' or 'peliculas' in url:
            new_item.action = 'findvideos'
            new_item.contentTitle = scrapedtitle
        else:
            new_item.action = 'seasons'
            new_item.contentSerieName = scrapedtitle

        itemlist.append(new_item)

    tmdb.set_infoLabels(itemlist, seekTmdb=True)
    #  Paginación

    url_next_page = scrapertools.find_single_match(data,'<link rel="next" href="([^"]+)"')
    if url_next_page:
        itemlist.append(item.clone(title="Siguiente >>", url=url_next_page, action='list_all'))

    return itemlist

def list_collections(item):
    logger.info()

    itemlist = []

    data = get_source(item.url)
    patron = '<li><a href="([^"]+)">.*?"first-lIMG"><img src="([^"]+)">.*?<h2>([^<]+)</h2>.*?Fichas:?\s(\d+)'

    matches = re.compile(patron, re.DOTALL).findall(data)

    for url, thumb, title, cant in matches:
        plot = 'Contiene %s elementos' % cant
        itemlist.append(Item(channel=item.channel, action='list_all', title=title, url=url, thumbnail=thumb, plot=plot))

    url_next_page = scrapertools.find_single_match(data, 'class="PageActiva">\d+</a><a href="([^"]+)"')
    if url_next_page:
        itemlist.append(item.clone(title="Siguiente >>", url=url_next_page, action='list_collections'))
    return itemlist

def seasons(item):
    logger.info()

    itemlist=[]

    data=get_source(item.url)
    patron='<div class="season temporada-(\d+)">'
    matches = re.compile(patron, re.DOTALL).findall(data)

    infoLabels = item.infoLabels
    for season in matches:
        season = season.lower().replace('temporada','')
        infoLabels['season']=season
        title = 'Temporada %s' % season
        itemlist.append(Item(channel=item.channel, title=title, url=item.url, action='episodesxseasons',
                             infoLabels=infoLabels))
    tmdb.set_infoLabels_itemlist(itemlist, seekTmdb=True)

    if config.get_videolibrary_support() and len(itemlist) > 0:
        itemlist.append(
                Item(channel=item.channel, title='[COLOR yellow]Añadir esta serie a la videoteca[/COLOR]', url=item.url,
                     action="add_serie_to_library", extra="episodios", contentSerieName=item.contentSerieName))

    return itemlist

def episodios(item):
    logger.info()
    itemlist = []
    templist = seasons(item)
    for tempitem in templist:
        itemlist += episodesxseasons(tempitem)

    return itemlist

def episodesxseasons(item):
    logger.info()

    itemlist = []

    data=get_source(item.url)
    patron= '<li><a href="([^"]+)"><b>%s - (\d+)</b><h2 class="eTitle">([^>]+)</h2>' % item.infoLabels['season']
    matches = re.compile(patron, re.DOTALL).findall(data)

    infoLabels = item.infoLabels

    for url, scrapedepisode, scrapedtitle in matches:

        infoLabels['episode'] = scrapedepisode
        title = '%sx%s - %s' % (infoLabels['season'], infoLabels['episode'], scrapedtitle)

        itemlist.append(Item(channel=item.channel, title= title, url=url, action='findvideos',
                             infoLabels=infoLabels))

    tmdb.set_infoLabels_itemlist(itemlist, seekTmdb=True)

    return itemlist

def findvideos(item):

    logger.info()

    itemlist = []

    data = get_source(item.url)
    data = data.replace('"', "'")
    patron = "onclick='clickLink\(this, '([^']+)', '([^']+)', '([^']+)'\);'>.*?<b>([a-zA-Z]+)"
    matches = re.compile(patron, re.DOTALL).findall(data)
    headers = {'referer': item.url}
    for url, quality, language, server in matches:

        if url != '':
            language = IDIOMAS[language]
            if quality.lower() == 'premium':
                quality = '720p'
            quality = CALIDADES[quality]
            title = ' [%s] [%s]' % (language, quality)
            if 'visor/vdz' in url:
                server = 'powvideo'
            itemlist.append(Item(channel=item.channel, title='%s' + title, url=url, action='play', language=language,
                                 quality=quality, server=server, headers=headers, infoLabels=item.infoLabels))
    itemlist = servertools.get_servers_itemlist(itemlist, lambda i: i.title % i.server.capitalize())
    return sorted(itemlist, key=lambda i: i.language)


def play(item):
    from lib.generictools import privatedecrypt
    logger.info()
    itemlist = []
    url = ''
    item.server = ''
    data = httptools.downloadpage(item.url, headers=item.headers, follow_redirects=False)
    if 'visor/vdz' in item.url:
        url = scrapertools.find_single_match(data.data, 'IFRAME SRC="([^"]+)"')
    elif 'visor/if' in item.url:
        url = data.headers['location']

    itemlist.append(Item(channel=item.channel, url=url, action='play', server=item.server,
                         infoLabels=item.infoLabels))

    itemlist = servertools.get_servers_itemlist(itemlist)
    return itemlist




def search(item, texto):
    logger.info()
    texto = texto.replace(" ", "+")
    item.url = item.url + texto
    item.type = 'peliculas'
    if texto != '':
        return list_all(item)
    else:
        return []

def newest(categoria):
    logger.info()
    itemlist = []
    item = Item()
    try:
        if categoria in ['peliculas']:
            item.url = host + 'peliculas'
        elif categoria == 'infantiles':
            item.url = host + 'peliculas/filtro/Animación,/,'
        elif categoria == 'terror':
            item.url = host + 'peliculas/filtro/Terror,/,'
        item.type='peliculas'
        itemlist = list_all(item)
        if itemlist[-1].title == 'Siguiente >>':
            itemlist.pop()
    except:
        import sys
        for line in sys.exc_info():
            logger.error("{0}".format(line))
        return []

    return itemlist
