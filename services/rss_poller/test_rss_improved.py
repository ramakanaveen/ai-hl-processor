#!/usr/bin/env python3
"""
Improved RSS Feed Tester with SSL handling
"""
import feedparser
import yaml
import ssl
import certifi
import urllib.request
from datetime import datetime

# Disable SSL verification for testing (not recommended for production)
ssl._create_default_https_context = ssl._create_unverified_context

def test_rss_feed(feed_config):
    """Test fetching and parsing a single RSS feed"""
    print(f"\n{'='*80}")
    print(f"Testing: {feed_config['name']}")
    print(f"URL: {feed_config['url']}")
    print(f"{'='*80}")

    try:
        # Parse the RSS feed
        print("Fetching feed...")
        feed = feedparser.parse(feed_config['url'])

        # Check for errors
        if feed.bozo:
            print(f"⚠️  Parse warning: {feed.bozo_exception}")

        # Check HTTP status
        if hasattr(feed, 'status'):
            print(f"HTTP Status: {feed.status}")

        # Display feed info
        feed_title = feed.feed.get('title', 'N/A')
        feed_desc = feed.feed.get('description', 'N/A')

        print(f"\n✓ Feed fetched successfully")
        print(f"  Title: {feed_title}")
        if len(feed_desc) > 100:
            print(f"  Description: {feed_desc[:100]}...")
        else:
            print(f"  Description: {feed_desc}")
        print(f"  Entries found: {len(feed.entries)}")

        # Display first 5 entries
        if feed.entries:
            print(f"\n📰 Latest Headlines (showing first 5):")
            print(f"{'-'*80}")

            for i, entry in enumerate(feed.entries[:5], 1):
                title = entry.get('title', 'No title')
                link = entry.get('link', 'No link')
                published = entry.get('published', 'No date')
                author = entry.get('author', 'Unknown')

                # Generate GUID like the actual poller does
                import hashlib
                content = f"{title}|{link}"
                guid = hashlib.sha256(content.encode()).hexdigest()[:16]

                print(f"\n{i}. {title}")
                print(f"   Published: {published}")
                print(f"   Author: {author}")
                print(f"   GUID: {guid}")
                if len(link) > 70:
                    print(f"   Link: {link[:70]}...")
                else:
                    print(f"   Link: {link}")

            return True, len(feed.entries)
        else:
            print("⚠️  No entries found in feed")
            return True, 0

    except Exception as e:
        print(f"✗ Error fetching feed: {e}")
        import traceback
        traceback.print_exc()
        return False, 0


def test_sample_feeds():
    """Test with some known working RSS feeds"""
    print("\n" + "="*80)
    print("TESTING WITH SAMPLE FEEDS (Known Working)")
    print("="*80)

    sample_feeds = [
        {
            "name": "BBC News - World",
            "url": "http://feeds.bbci.co.uk/news/world/rss.xml"
        },
        {
            "name": "CNN Top Stories",
            "url": "http://rss.cnn.com/rss/cnn_topstories.rss"
        },
        {
            "name": "Reuters World News",
            "url": "https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best"
        }
    ]

    results = []
    for feed_config in sample_feeds:
        success, count = test_rss_feed(feed_config)
        results.append((feed_config['name'], success, count))

    return results


def main():
    """Test all RSS feeds from config"""
    print("RSS Feed Tester (with SSL handling)")
    print("="*80)

    # Test configured feeds
    try:
        with open("config.yaml") as f:
            config = yaml.safe_load(f)

        feeds = config.get('feeds', [])
        print(f"\nFound {len(feeds)} feed(s) in configuration")

        # Test each configured feed
        results = []
        for feed_config in feeds:
            success, count = test_rss_feed(feed_config)
            results.append((feed_config['name'], success, count))

        # Test sample feeds
        sample_results = test_sample_feeds()

        # Combined summary
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")

        print("\nConfigured Feeds:")
        total_entries = 0
        for name, success, count in results:
            status = "✓ PASS" if success else "✗ FAIL"
            print(f"  {status} - {name} ({count} entries)")
            total_entries += count

        print(f"\nSample Feeds:")
        sample_entries = 0
        for name, success, count in sample_results:
            status = "✓ PASS" if success else "✗ FAIL"
            print(f"  {status} - {name} ({count} entries)")
            sample_entries += count

        print(f"\nTotal entries from configured feeds: {total_entries}")
        print(f"Total entries from sample feeds: {sample_entries}")

        if total_entries == 0:
            print("\n⚠️  No entries found from configured feeds.")
            print("Recommendation: Update config.yaml with working RSS feed URLs")
            print("\nWorking alternatives to try:")
            print("  - http://feeds.bbci.co.uk/news/world/rss.xml")
            print("  - http://rss.cnn.com/rss/cnn_topstories.rss")
            print("  - https://feeds.a.dj.com/rss/RSSWorldNews.xml (Wall Street Journal)")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
