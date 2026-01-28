#!/usr/bin/env python
"""Test script to verify Arize AX credentials with SDK v8."""

import os


def test_credentials():
    """Test Arize AX API credentials."""

    api_key = os.environ.get("ARIZE_API_KEY")
    space_id = os.environ.get("ARIZE_SPACE_ID")

    if not api_key:
        print("ARIZE_API_KEY not set")
        return False
    if not space_id:
        print("ARIZE_SPACE_ID not set")
        return False

    print(f"API Key: {api_key[:10]}...{api_key[-5:]}")
    print(f"Space ID: {space_id}")
    print()

    # Test 1: REST API v2 (datasets)
    print("=== Test 1: REST API v2 (datasets) ===")
    try:
        import httpx

        response = httpx.get(
            "https://api.arize.com/v2/datasets",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        if response.status_code == 200:
            data = response.json()
            datasets = data.get("datasets", [])
            print(f"REST API works! Found {len(datasets)} datasets")
        else:
            print(f"REST API error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"REST API exception: {e}")

    print()

    # Test 2: REST API v2 (experiments)
    print("=== Test 2: REST API v2 (experiments) ===")
    try:
        response = httpx.get(
            "https://api.arize.com/v2/experiments",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        if response.status_code == 200:
            data = response.json()
            experiments = data.get("experiments", [])
            print(f"REST API works! Found {len(experiments)} experiments")
        else:
            print(f"REST API error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"REST API exception: {e}")

    print()

    # Test 3: Arize SDK v8 Client
    print("=== Test 3: Arize SDK v8 (ArizeClient) ===")
    try:
        from arize import ArizeClient

        client = ArizeClient(api_key=api_key)
        print(f"ArizeClient initialized successfully")
        print(f"  Available resources: spans, datasets, experiments, models")

        # Try to list datasets via SDK
        print("\n  Testing client.datasets.list()...")
        try:
            datasets = client.datasets.list(space_id=space_id)
            print(f"  Datasets: {len(datasets)} found")
        except Exception as e:
            print(f"  Datasets error: {e}")

    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure arize>=8.0.0 is installed")
    except Exception as e:
        print(f"ArizeClient exception: {e}")

    print()

    # Test 4: Arize SDK v8 Spans Export
    print("=== Test 4: Arize SDK v8 (spans.export_to_df) ===")
    try:
        from arize import ArizeClient
        from datetime import datetime, timedelta, timezone

        client = ArizeClient(api_key=api_key)
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=1)

        print("Attempting to export spans (with test project)...")
        try:
            df = client.spans.export_to_df(
                space_id=space_id,
                project_name="__test__",  # This will likely fail but shows auth
                start_time=start_time,
                end_time=end_time,
            )
            print(f"Export works! Got {len(df)} spans")
        except Exception as e:
            error_str = str(e).lower()
            if "unauthenticated" in error_str or "api key" in error_str:
                print(f"Authentication failed: {e}")
            elif "not found" in error_str or "project" in error_str:
                print(f"Authentication works! (project not found is expected)")
            else:
                print(f"Error: {e}")
    except ImportError as e:
        print(f"Import error: {e}")
    except Exception as e:
        print(f"Exception: {e}")

    print()

    # Test 5: GraphQL API
    print("=== Test 5: GraphQL API ===")
    try:
        response = httpx.post(
            "https://app.arize.com/graphql",
            json={"query": "query { viewer { user { name } }}"},
            headers={"x-api-key": api_key, "Content-Type": "application/json"},
            timeout=30.0,
        )
        if response.status_code == 200:
            data = response.json()
            if "data" in data and data["data"].get("viewer"):
                user_name = data["data"]["viewer"]["user"]["name"]
                print(f"GraphQL API works! User: {user_name}")
            elif "errors" in data:
                print(f"GraphQL error: {data['errors']}")
            else:
                print(f"GraphQL unexpected data: {data}")
        else:
            print(f"GraphQL API error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"GraphQL API exception: {e}")

    print()
    print("=== Summary ===")
    print("- REST API v2 (datasets/experiments): Uses 'Authorization: Bearer <key>'")
    print("- Arize SDK v8: Unified client with client.spans, client.datasets, etc.")
    print("- GraphQL API: Uses 'x-api-key: <key>' header (requires developer permissions)")
    print()
    print("If REST API works, datasets and experiments tools should work.")
    print("If SDK v8 spans.export_to_df works with a known project, trace tools will work.")


if __name__ == "__main__":
    test_credentials()
