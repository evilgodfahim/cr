#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import feedparser
import os
from datetime import datetime, timedelta, timezone
from dateutil import parser as dateparser
from lxml import etree

FEEDS = [
    "https://feeds.guardian.co.uk/theguardian/environment/rss",
    "https://www.theguardian.com/environment/climate-crisis/rss",
    "https://www.theguardian.com/news/series/the-long-read/rss",
    "https://www.theguardian.com/uk/commentisfree/rss",
    "https://www.theguardian.com/international/rss",
    "https://feeds.guardian.co.uk/theguardian/world/rss",
]

OUTPUT = "merged.xml"
MAX_ITEMS = 1000
CUTOFF = datetime.now(timezone.utc) - timedelta(hours=48)

def load_existing_links(root):
    links = set()
    for item in root.xpath("//item/link"):
        if item.text:
            links.add(item.text.strip())
    return links

def parse_datetime(entry):
    if hasattr(entry, "published"):
        return dateparser.parse(entry.published).astimezone(timezone.utc)
    return None

def extract_image(entry):
    if "media_content" in entry and entry.media_content:
        return entry.media_content[0].get("url")
    if "links" in entry:
        for l in entry.links:
            if l.get("type", "").startswith("image"):
                return l.get("href")
    return None

if os.path.exists(OUTPUT):
    tree = etree.parse(OUTPUT)
    channel = tree.find(".//channel")
    existing_links = load_existing_links(tree)
else:
    rss = etree.Element("rss", version="2.0", nsmap={"media": "http://search.yahoo.com/mrss/"})
    channel = etree.SubElement(rss, "channel")
    etree.SubElement(channel, "title").text = "Guardian Unified Feed"
    etree.SubElement(channel, "link").text = "https://www.theguardian.com"
    etree.SubElement(channel, "description").text = "Merged Guardian RSS"
    tree = etree.ElementTree(rss)
    existing_links = set()

new_items = []

for url in FEEDS:
    feed = feedparser.parse(url)
    for entry in feed.entries:
        dt = parse_datetime(entry)
        if not dt or dt < CUTOFF:
            continue

        link = entry.get("link")
        if not link or link in existing_links:
            continue

        item = etree.Element("item")
        etree.SubElement(item, "title").text = entry.get("title", "").strip()
        etree.SubElement(item, "link").text = link
        etree.SubElement(item, "guid").text = link
        etree.SubElement(item, "pubDate").text = dt.strftime("%a, %d %b %Y %H:%M:%S %z")

        desc = entry.get("summary", "")
        if desc:
            etree.SubElement(item, "description").text = desc

        img = extract_image(entry)
        if img:
            media = etree.SubElement(item, "{http://search.yahoo.com/mrss/}content")
            media.set("url", img)
            media.set("medium", "image")

        new_items.append((dt, item))
        existing_links.add(link)

new_items.sort(key=lambda x: x[0], reverse=True)

for _, item in new_items:
    channel.insert(0, item)

items = channel.findall("item")
if len(items) > MAX_ITEMS:
    for i in items[MAX_ITEMS:]:
        channel.remove(i)

tree.write(
    OUTPUT,
    encoding="utf-8",
    xml_declaration=True,
    pretty_print=True
)
