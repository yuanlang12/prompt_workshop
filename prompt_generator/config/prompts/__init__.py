import os

def load_metaprompt():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    metaprompt_path = os.path.join(current_dir, 'metaprompt.txt')
    
    try:
        with open(metaprompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error loading metaprompt: {e}")
        return None

METAPROMPT = load_metaprompt() 