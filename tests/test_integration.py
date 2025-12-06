import os
import yaml
import subprocess
from vibetest.persona_generator import PersonaGenerator

def test_integration():
    print("--- Testing PersonaGenerator Skeleton Generation ---")
    # 1. Create a dummy blueprint
    blueprint = {
        "name": "{{ choice('Alice', 'Bob') }}",
        "age": "{{ range(20, 30) }}",
        "stats": {
            "strength": "{{ normal(10, 2) }}",
            "magic": "{{ bool(0.5) }}"
        }
    }
    
    with open("dummy_blueprint.yaml", "w") as f:
        yaml.dump(blueprint, f)
    
    # 2. Initialize Generator (mocking project path to current dir)
    # We need to be careful about the blueprint path expected by the generator
    # The generator expects blueprint.yaml in the project_path.
    # So let's use the current directory as the project path for this test.
    
    # Rename dummy to blueprint.yaml temporarily if needed, or just use 'blueprint.yaml'
    with open("blueprint.yaml", "w") as f:
        yaml.dump(blueprint, f)

    try:
        gen = PersonaGenerator(project_path=".")
        skeleton = gen.generate_skeleton(gen.load_blueprint())
        print("Generated Skeleton:")
        print(skeleton)
        
        assert skeleton['name'] in ['Alice', 'Bob']
        assert 20 <= int(skeleton['age']) <= 30
        assert isinstance(skeleton['stats']['strength'], int)
        assert isinstance(skeleton['stats']['magic'], bool)
        print("✓ Skeleton generation successful")

        print("--- Testing LLM Integration (Flesh out Persona) ---")
        # This will actually hit the API, so it might cost a tiny bit or fail if key is wrong
        persona_content = gen.flesh_out_persona(skeleton)
        print("Generated Persona Content Preview:")
        print(persona_content[:200] + "...")
        
        if "stats" in persona_content or "Alice" in persona_content or "Bob" in persona_content:
             print("✓ LLM response received and seems relevant")
        else:
             print("? LLM response received but might be generic")
        
    except Exception as e:
        print(f"✗ Generator failed: {e}")
    finally:
        # Cleanup
        if os.path.exists("blueprint.yaml"):
            os.remove("blueprint.yaml")
        if os.path.exists("dummy_blueprint.yaml"):
            os.remove("dummy_blueprint.yaml")

    print("\n--- Testing CLI Entry Point ---")
    try:
        result = subprocess.run(["python", "main.py", "--help"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ CLI help command ran successfully")
            print(result.stdout[:200] + "...") # Show first 200 chars
        else:
            print("✗ CLI failed to run")
            print(result.stderr)
    except Exception as e:
        print(f"✗ CLI execution failed: {e}")

if __name__ == "__main__":
    test_integration()
