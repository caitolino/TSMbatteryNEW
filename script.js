fetch('http://TSM-5CD2182GXS:27017/collected_data/batterijbeheer')
.then(res => res.json())
.then(batterijen => {
    const list = document.getElementById("data-list");
      items.forEach(item => {
        const li = document.createElement("li")
        
        li.textContent = JSON.stringify(item);
        list.appendChild(li);
        });
    })

        .catch(err => console.error("error getting data:", err));