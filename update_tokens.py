import os
import json
import time
import requests
from github import Github
from concurrent.futures import ThreadPoolExecutor, as_completed

API_URL = "https://jwt-v1.vercel.app/token"
MAX_WORKERS = 5       # Bir vaqtning o‘zida maksimal 5 so‘rov
MAX_RETRIES = 3       # Har bir UID uchun 3 marta qayta urinish

def generate_token(uid, password):
    """UID uchun token olish, 3 marta qayta urinish bilan"""
    url = f"{API_URL}?uid={uid}&password={password}"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()

            token = data.get("token") or data.get("BearerAuth")
            if token:
                return {"uid": data.get("uid", uid), "token": token}

            raise ValueError("Invalid API response format")

        except Exception as e:
            print(f"[{attempt}/{MAX_RETRIES}] ⚠️ UID {uid}: {e}")
            time.sleep(3)

    return {"uid": uid, "error": "Failed after retries"}

def process_region(region, repo):
    input_file = f"input_{region}.json"
    output_file = f"token_{region}.json"

    try:
        contents = repo.get_contents(input_file)
        input_data = json.loads(contents.decoded_content.decode())
    except Exception as e:
        print(f"[!] Could not read {input_file}: {e}")
        return

    print(f"[*] Processing {len(input_data)} accounts for region {region}...")

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(generate_token, item["uid"], item["password"]): item["uid"]
            for item in input_data if item.get("uid") and item.get("password")
        }

        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            if "token" in result:
                print(f"[+] {result['uid']} ✅ Token olindi")
            else:
                print(f"[x] {result['uid']} ❌ {result['error']}")
            time.sleep(0.3)  # So‘rovlar orasida ozgina pauza

    if not results:
        print(f"[!] No tokens generated for {region}")
        return

    # JSONni tozalash (error yozuvlarini chiqarib tashlash)
    cleaned_results = [r for r in results if "token" in r]

    output_content = json.dumps(cleaned_results, indent=2)
    try:
        try:
            existing = repo.get_contents(output_file)
            repo.update_file(
                output_file,
                f"🔄 Auto update tokens for {region}",
                output_content,
                existing.sha
            )
            print(f"[✔] Updated {output_file} on GitHub ({len(cleaned_results)} token)")
        except:
            repo.create_file(
                output_file,
                f"🆕 Add tokens for {region}",
                output_content
            )
            print(f"[✔] Created {output_file} on GitHub")
    except Exception as e:
        print(f"[!] Failed to write {output_file}: {e}")

if __name__ == "__main__":
    gh_token = os.getenv("GITHUB_TOKEN")
    if not gh_token:
        print("❌ GITHUB_TOKEN topilmadi (env o‘zgaruvchi kerak)")
        exit(1)

    g = Github(gh_token)
    repo = g.get_repo("aruzpanel/fflikes-aruz")

    regions = ["ind", "sg", "bd"]
    for region in regions:
        process_region(region, repo)
