#!/bin/bash

# Update GitHub Actions to latest versions
echo "Updating GitHub Actions versions across workflow files..."

# Function to update actions in a file
update_file() {
    local file=$1
    echo "Updating $file..."
    
    # Update common actions to latest versions
    sed -i 's/actions\/cache@v[0-9]*/actions\/cache@v4/g' "$file"
    sed -i 's/actions\/upload-artifact@v[0-9]*/actions\/upload-artifact@v4/g' "$file"
    sed -i 's/actions\/download-artifact@v[0-9]*/actions\/download-artifact@v4/g' "$file"
    sed -i 's/codecov\/codecov-action@v[0-9]*/codecov\/codecov-action@v5/g' "$file"
    sed -i 's/docker\/build-push-action@v[0-9]*/docker\/build-push-action@v6/g' "$file"
    sed -i 's/docker\/setup-buildx-action@v[0-9]*/docker\/setup-buildx-action@v3/g' "$file"
    sed -i 's/docker\/login-action@v[0-9]*/docker\/login-action@v3/g' "$file"
    sed -i 's/github\/codeql-action\/[a-z]*@v[0-9]*/&/g' "$file"  # Keep current CodeQL version
    sed -i 's/paambaati\/codeclimate-action@v[0-9.]*/paambaati\/codeclimate-action@v9.0.0/g' "$file"
    sed -i 's/softprops\/action-gh-release@v[0-9]*/softprops\/action-gh-release@v2/g' "$file"
    sed -i 's/actions\/create-release@v[0-9]*/softprops\/action-gh-release@v2/g' "$file"
}

# Update all workflow files
for file in .github/workflows/*.yml; do
    if [ -f "$file" ]; then
        update_file "$file"
    fi
done

echo "GitHub Actions versions updated!"