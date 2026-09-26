let camera, scene, renderer, loader, light1, light2, controls, model;

init();
animate();

function init() {

    let url = (document.URL.split('?')[1] || "example/suzanne.obja");

    loader = new Loader(url, 1024, 20);
    loader.start(function(elements) {
        for (let element of elements) {
            if (element !== undefined) {
                try {
                    model.manageElement(element);
                } catch(e) {
                    if (e.type === "custom") {
                        document.getElementById('errormessage').innerHTML = e;
                    } else {
                        throw e;
                    }
                }
            }
        }
    });

    camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.0001, 1000);
    camera.position.z = 3;

    scene = new THREE.Scene();

    model = new Model(url);
    scene.add(model);

    light1 = new THREE.AmbientLight(0x999999);
    scene.add(light1);

    light2 = new THREE.DirectionalLight(0xffffff, 1.0);
    light2.position.set(0.0, 1.0, 0.0);
    scene.add(light2);

    renderer = new THREE.WebGLRenderer({antialias: true});
    renderer.setSize(window.innerWidth, window.innerHeight);
    document.body.appendChild(renderer.domElement);

    window.addEventListener('resize', onWindowResize, false);
    controls = new THREE.OrbitControls(camera, renderer.domElement);

}

function animate() {

    requestAnimationFrame(animate);
    controls.update();
    document.getElementById('progressbar').value = Math.floor(100 * loader.percentage()) || 0;
    document.getElementById('percentage').innerHTML = Math.floor(100 * loader.percentage()) / 100 + "%";
    renderer.render(scene, camera);

}

function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();

    renderer.setSize( window.innerWidth, window.innerHeight );
}
