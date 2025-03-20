import requests
import asyncio
import aiohttp

# **API の設定**
BASE_URL = "http://localhost:8080"
API_KEY = "bcb37e59225eb6ff71f9ee169e27a810a9c8d5d5"

headers = {"Authorization": f"Token {API_KEY}"}

# **1️⃣ プロジェクト一覧を取得**
def get_projects():
    response = requests.get(f"{BASE_URL}/api/projects", headers=headers)

    if response.status_code != 200:
        print(f"❌ APIの取得に失敗しました: {response.status_code}")
        print(response.text)
        return []

    projects = response.json().get("results", [])

    # **プロジェクト一覧を表示**
    print("\n📌 **Label Studio プロジェクト一覧**")
    if not projects:
        print("❌ プロジェクトが見つかりませんでした。")
        return []

    for project in projects:
        print(f"🆔 ID: {project['id']} - 📂 プロジェクト名: {project['title']}")

    return projects

# **2️⃣ 指定したプロジェクトのラベル一覧を取得**
def get_project_labels(project_id):
    response = requests.get(f"{BASE_URL}/api/projects/{project_id}", headers=headers)

    if response.status_code != 200:
        print(f"❌ プロジェクト {project_id} の取得に失敗しました: {response.status_code}")
        return None

    project_data = response.json()
    parsed_config = project_data.get("parsed_label_config", {})

    labels = parsed_config.get("label", {}).get("labels", [])
    label_dict = {i+1: label for i, label in enumerate(labels)}  # ラベルに番号を振る

    return label_dict

# **3️⃣ 既存のアノテーションを一括更新**
async def update_annotations(session, annotation_id, old_label, new_label):
    async with session.get(f"{BASE_URL}/api/annotations/{annotation_id}", headers=headers) as response:
        if response.status != 200:
            print(f"❌ アノテーション {annotation_id} の取得に失敗: {response.status}")
            return
        
        annotation = await response.json()
        updated_result = []

        for item in annotation["result"]:
            if item["value"].get("rectanglelabels") == [old_label]:
                item["value"]["rectanglelabels"] = [new_label]
            updated_result.append(item)

        update_data = {"result": updated_result}

        async with session.patch(f"{BASE_URL}/api/annotations/{annotation_id}", headers=headers, json=update_data) as update_response:
            if update_response.status == 200:
                print(f"✅ アノテーション {annotation_id} のラベル '{old_label}' を '{new_label}' に変更しました！")
            else:
                print(f"❌ アノテーションの更新に失敗しました: {update_response.status}")

# **4️⃣ 全アノテーションを並列更新**
async def bulk_update_annotations(project_id, old_label, new_label):
    async with aiohttp.ClientSession() as session:
        response = await session.get(f"{BASE_URL}/api/projects/{project_id}/tasks", headers=headers)
        if response.status != 200:
            print(f"❌ プロジェクト {project_id} のタスク取得に失敗: {response.status}")
            return

        tasks = await response.json()
        annotation_tasks = []

        for task in tasks:
            for annotation in task.get("annotations", []):
                annotation_id = annotation["id"]
                annotation_tasks.append(update_annotations(session, annotation_id, old_label, new_label))

        await asyncio.gather(*annotation_tasks)  # **全ての更新処理を並列実行**

# **5️⃣ ラベルを変更**
def update_project_label(project_id, old_label, new_label):
    response = requests.get(f"{BASE_URL}/api/projects/{project_id}", headers=headers)
    if response.status_code != 200:
        print(f"❌ プロジェクト {project_id} の取得に失敗しました: {response.status_code}")
        return

    project_data = response.json()
    label_config = project_data.get("label_config", "")

    # **ラベルを置換**
    updated_config = label_config.replace(f'value="{old_label}"', f'value="{new_label}"')

    update_data = {"label_config": updated_config}
    response = requests.patch(f"{BASE_URL}/api/projects/{project_id}", headers=headers, json=update_data)

    if response.status_code == 200:
        print(f"✅ プロジェクト {project_id} のラベル '{old_label}' を '{new_label}' に変更しました！")
        asyncio.run(bulk_update_annotations(project_id, old_label, new_label))  # **非同期でアノテーションを一括更新**
    else:
        print(f"❌ ラベルの変更に失敗しました: {response.status_code}")

# **6️⃣ ユーザー入力でラベルを変更**
def main():
    projects = get_projects()

    if not projects:
        print("❌ プロジェクトが見つかりませんでした。")
        return

    # **ユーザーにプロジェクトを選択させる**
    project_id = int(input("\n🔢 ラベルを変更するプロジェクト ID を入力: "))

    labels = get_project_labels(project_id)
    if not labels:
        print("❌ 指定したプロジェクトのラベルが見つかりませんでした。")
        return

    # **ラベル一覧を表示**
    print("\n🏷️ **現在のラベル一覧**")
    for num, label in labels.items():
        print(f"{num}: {label}")

    # **変更するラベルを選択**
    label_num = int(input("\n🔢 変更するラベルの番号を入力: "))
    if label_num not in labels:
        print("❌ 無効な番号です。")
        return

    old_label = labels[label_num]
    new_label = input("📝 新しいラベル名を入力: ")

    # **ラベルを変更**
    update_project_label(project_id, old_label, new_label)

if __name__ == "__main__":
    main()
