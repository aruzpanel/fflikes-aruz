import os
import json
import requests
from github import Github
from concurrent.futures import ThreadPoolExecutor

def generate_token(uid, password):
    url = f"https://jwt-aruz.vercel.app/token?uid={uid}&password={password}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Ensure the response contains the 'access_token' field
        if "access_token" in data:
            return data["access_token"]
        else:
            raise ValueError("Unexpected API response format: 'access_token' not found")
    except Exception as e:
        print(f"[!] Token generation failed for UID {uid}: {e}")
        return None

def process_region(region, repo):
    input_file = f"input_{region}.json"
    output_file = f"token_{region}.json"

    try:
        contents = repo.get_contents(input_file)
        input_data = json.loads(contents.decoded_content.decode())
    except Exception as e:
        print(f"[!] Could not read {input_file}: {e}")
        return

    tokens = []

    # Use ThreadPoolExecutor to process token generation in parallel
    with ThreadPoolExecutor() as executor:
        futures = []
        for entry in input_data:
            uid = entry.get("uid")
            password = entry.get("password")
            if not uid or not password:
                print(f"[!] Skipping entry due to missing UID or password: {entry}")
                continue
            # Submit the token generation task to the thread pool
            futures.append(executor.submit(generate_token, uid, password))

        # Collect the results as they finish
        for future in futures:
            token = future.result()
            if token:
                tokens.append({"uid": future.args[0], "token": token})

    if not tokens:
        print(f"[!] No tokens generated for {region}")
        return

    try:
        output_content = json.dumps(tokens, indent=2)

        try:
            existing_file = repo.get_contents(output_file)
            repo.update_file(output_file, f"Update tokens for {region}", output_content, existing_file.sha)
        except:
            repo.create_file(output_file, f"Create tokens for {region}", output_content)
        print(f"[✓] Token file saved: {output_file}")
    except Exception as e:
        print(f"[!] Error saving {output_file}: {e}")

def main():
    try:
        github_token = os.getenv("GITHUB_TOKEN")
        repository_name = os.getenv("GITHUB_REPOSITORY")
        if not github_token or not repository_name:
            raise ValueError("Missing GITHUB_TOKEN or GITHUB_REPOSITORY environment variable.")

        g = Github(github_token)
        repo = g.get_repo(repository_name)

        # Use ThreadPoolExecutor for region processing in parallel
        with ThreadPoolExecutor() as executor:
            executor.map(lambda region: process_region(region, repo), ["bd", "ind", "sg"])

    except Exception as e:
        print(f"[!] Workflow failed: {e}")

if __name__ == "__main__":
    main()
