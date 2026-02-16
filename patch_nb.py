import json

def patch_nb():
    path = '05_model_training.ipynb'
    with open(path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    for c in nb['cells']:
        if c['cell_type'] == 'code':
            src = "".join(c['source'])
            if "SEASONS = [2021, 2022, 2023, 2024]" in src:
                c['source'] = src.replace("SEASONS = [2021, 2022, 2023, 2024]", 
                                          "SEASONS = [2021, 2022, 2023, 2024]\nSEASON = SEASONS").splitlines(keepends=True)
                print("Patched SEASONS -> SEASON alias")
                break
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1)

if __name__ == '__main__':
    patch_nb()
