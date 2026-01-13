#!/usr/bin/env python3
"""
Test RSS Feed Fetching
Quick test to verify RSS feeds are accessible and can be parsed
"""
import feedparser
import yaml
from datetime import datetime

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
            print(f"⚠️  Warning: {feed.bozo_exception}")

        # Display feed info
        print(f"\n✓ Feed fetched successfully")
        print(f"  Title: {feed.feed.get('title', 'N/A')}")
        print(f"  Description: {feed.feed.get('description', 'N/A')[:100]}...")
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

                print(f"\n{i}. {title}")
                print(f"   Published: {published}")
                print(f"   Author: {author}")
                print(f"   Link: {link[:60]}...")
        else:
            print("⚠️  No entries found in feed")

        return True

    except Exception as e:
        print(f"✗ Error fetching feed: {e}")
        return False


def main():
    """Test all RSS feeds from config"""
    print("RSS Feed Tester")
    print("="*80)

    # Load configuration
    try:
        with open("config.yaml") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return

    feeds = config.get('feeds', [])
    print(f"\nFound {len(feeds)} feed(s) in configuration")

    # Test each feed
    results = []
    for feed_config in feeds:
        success = test_rss_feed(feed_config)
        results.append((feed_config['name'], success))

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")

    successful = sum(1 for _, success in results if success)
    print(f"\nTotal feeds tested: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(results) - successful}")

    print("\nFeed Status:")
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status} - {name}")

    print()


if __name__ == "__main__":
    main()
