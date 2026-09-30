"""
Test script to compare bare keyword vs all: prefix queries on arxiv API.
"""
import arxiv
import time
import logging

logging.basicConfig(
    format='[%(asctime)s %(levelname)s] %(message)s',
    datefmt='%m/%d/%Y %H:%M:%S',
    level=logging.INFO
)

# Build query variants
def build_query_variant(variant):
    group_a = 'memory'
    group_b_terms = ['agent', 'LLM', 'LLMs', '"language model"', '"language models"']
    group_c_terms = [
        'attack', 'defense', 'safety', 'red-team', 'red-teaming',
        'jailbreak', 'jailbreaks', 'poison', 'poisoning', 'malicious',
        'hijack', 'hijacking', 'adversarial', 'vulnerability', 'vulnerabilities',
        'threat', 'threats', 'risk', 'risks', 'protect', 'protection',
        'secure', 'security', 'harm', 'harmful', 'toxic', 'toxicity',
        'injection', 'extraction', 'leakage',
    ]

    if variant == 'bare':
        # Current: all bare keywords
        group_a_str = group_a
        group_b_str = f'({" OR ".join(group_b_terms)})'
        group_c_str = f'({" OR ".join(group_c_terms)})'
    elif variant == 'group_a_all':
        # Group A with all:, B and C bare
        group_a_str = f'all:"{group_a}"'
        group_b_str = f'({" OR ".join(group_b_terms)})'
        group_c_str = f'({" OR ".join(group_c_terms)})'
    elif variant == 'all_all':
        # All groups with all:
        group_a_str = f'all:"{group_a}"'
        group_b_str = f'({" OR ".join(f"all:{t}" for t in group_b_terms)})'
        group_c_str = f'({" OR ".join(f"all:{t}" for t in group_c_terms)})'
    else:
        raise ValueError(f"Unknown variant: {variant}")

    return f'{group_a_str} AND {group_b_str} AND {group_c_str}'


def test_query(variant, max_results=3):
    """Test a query variant and return results."""
    query = build_query_variant(variant)
    logging.info(f"\n{'='*60}")
    logging.info(f"TEST VARIANT: {variant}")
    logging.info(f"Query: {query}")

    client = arxiv.Client(
        page_size=100,
        delay_seconds=10.0,
        num_retries=5
    )
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )

    start_time = time.time()
    results = []
    total_results = None
    error = None

    try:
        # First, try to get total count from client
        # The arxiv library doesn't expose total directly, but we can check the last_result
        results_iter = client.results(search)
        count = 0
        for r in results_iter:
            results.append(r)
            count += 1
            if count >= max_results:
                break
    except Exception as e:
        error = str(e)
        logging.error(f"Error: {e}")

    elapsed = time.time() - start_time

    return {
        'variant': variant,
        'query': query,
        'results_count': len(results),
        'error': error,
        'elapsed': elapsed,
    }


def main():
    variants = ['bare', 'group_a_all', 'all_all']
    results = []

    for v in variants:
        # Add delay between queries to respect rate limits
        if v != 'bare':
            logging.info("Waiting 15s before next query...")
            time.sleep(15)

        result = test_query(v, max_results=3)
        results.append(result)

    # Summary
    logging.info(f"\n{'='*60}")
    logging.info("SUMMARY")
    logging.info(f"{'='*60}")
    for r in results:
        logging.info(f"Variant: {r['variant']}")
        logging.info(f"  Results returned: {r['results_count']}")
        logging.info(f"  Error: {r['error'] or 'None'}")
        logging.info(f"  Time: {r['elapsed']:.1f}s")
        logging.info(f"  Query: {r['query'][:100]}...")
        logging.info("")

    return results


if __name__ == "__main__":
    main()