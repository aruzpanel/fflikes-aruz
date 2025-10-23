import os
import json
import requests
from github import Github
from concurrent.futures import ThreadPoolExecutor, as_completed

API_URL = "https://jwt-aruz.vercel.app/token"

def generate_token(uid, password):
    """UID uchun token olish (parallel ishlash uchun optimallashtirilgan)"""
    url = f"{API_URL}?uid={uid}&password={password}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and "token" in data and "uid" in data:
            return {"uid": data["uid"], "token": data["token"]}
        else:
            return {"uid": uid, "error": "Invalid API format"}
    except Exception as e:
        return {"uid": uid, "error": str(e)}

def process_region(region, repo):
    input_file = f"input_{region}.json"
    output_file = f"token_{region}.json"

    # 🔹 JSON faylni olish
    try:
        contents = repo.get_contents(input_file)
        input_data = json.loads(contents.decoded_content.decode())
    except Exception as e:
        print(f"[!] Could not read {input_file}: {e}")
        return

    print(f"[*] Processing {len(input_data)} accounts for region {region}...")

    # 🔹 Parallel so‘rovlar (bir vaqtda 20 ta)
    results = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_uid = {
            executor.submit(generate_token, item["uid"], item["password"]): item["uid"]
            for item in input_data if item.get("uid") and item.get("password")
        }

        for future in as_completed(future_to_uid):
            result = future.result()
            results.append(result)
            if "token" in result:
                print(f"[+] {result['uid']} ✅ Token olindi")
            else:
                print(f"[x] {result['uid']} ❌ {result.get('error')}")

    if not results:
        print(f"[!] No tokens generated for {region}")
        return

    # 🔹 GitHub faylni yangilash
    try:
        output_content = json.dumps(results, indent=2)
        try:
            existing = repo.get_contents(output_file)
            repo.update_file(
                output_file,
                f"🔄 Update tokens for {region}",
                output_content,
                existing.sha
            )
            print(f"[✔] Updated {output_file} on GitHub")
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

    regions = ["ind", "sg"]  # kerak bo‘lsa boshqalarini qo‘shing
    for region in regions:
        process_region(region, repo)
