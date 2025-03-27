/*!
* Start Bootstrap - Clean Blog v6.0.9 (https://startbootstrap.com/theme/clean-blog)
* Copyright 2013-2023 Start Bootstrap
* Licensed under MIT (https://github.com/StartBootstrap/startbootstrap-clean-blog/blob/master/LICENSE)
*/
/* Scroll function */
window.addEventListener('DOMContentLoaded', () => {
    let scrollPos = 0;
    const mainNav = document.getElementById('mainNav');
    const headerHeight = mainNav.clientHeight;
    window.addEventListener('scroll', function() {
        const currentTop = document.body.getBoundingClientRect().top * -1;
        if ( currentTop < scrollPos) {
            // Scrolling Up
            if (currentTop > 0 && mainNav.classList.contains('is-fixed')) {
                mainNav.classList.add('is-visible');
            } else {
                console.log(123);
                mainNav.classList.remove('is-visible', 'is-fixed');
            }
        } else {
            // Scrolling Down
            mainNav.classList.remove(['is-visible']);
            if (currentTop > headerHeight && !mainNav.classList.contains('is-fixed')) {
                mainNav.classList.add('is-fixed');
            }
        }
        scrollPos = currentTop;
    });
})

document.addEventListener('DOMContentLoaded', function() {
    if (window.location.pathname === '/') {
        /* index.html: Previous Posts loads next 6 posts */
        const prevPostsButton = document.getElementById('previous-posts-button');
        if (prevPostsButton) {
            const postContainer = document.getElementById('post-container');
            const loadCount = 6;
            let visibleCount = visiblePostsInitialCount;

            function attachDeleteListeners() {
                const deleteLinks = document.querySelectorAll('.delete-post');
                deleteLinks.forEach(link => {
                    link.addEventListener('click', function(event) {
                        event.preventDefault();
                        const postId = this.dataset.postId;
                        const deleteForm = document.getElementById('deleteForm' + postId);
                        if (deleteForm) {
                            deleteForm.style.display = 'block';
                            deleteForm.action = `/delete-post/${postId}`;
                        }
                    });
                });
            }

            prevPostsButton.addEventListener('click', function() {
                let nextPosts = allPosts.slice(visibleCount, visibleCount + loadCount);

                if (nextPosts.length > 0) {
                    nextPosts.forEach(post => {
                        let deleteLink = '';
                        let deleteFormHtml = ''; // Initialize form html.

                        if (currentUserId === 1) {
                            deleteLink = `<a href="#" class="delete-post" data-post-id="${post.id}">✘</a>`;
                            deleteFormHtml = `
                                <form method="POST" action="/delete-post/${post.id}" id="deleteForm${post.id}" style="display: none;">
                                    <input type="password" name="delCode" style="font-size: 0.8em" placeholder="  Deletion Code">
                                    <button type="submit" class="btn btn-outline-danger btn-sm" style="font-size: 0.8em">Confirm Delete</button>
                                </form>
                            `;
                        }

                        const postDiv = document.createElement('div');
                        postDiv.classList.add('post-preview');
                        postDiv.innerHTML = `
                            <a href="/post/${post.id}">
                                <h2 class="post-title">${post.title}</h2>
                                <h3 class="post-subtitle">${post.subtitle}</h3>
                            </a>
                            <p class="post-meta">Posted by
                                <a href="#">${post.author.name}</a> on ${post.date}
                                ${deleteLink}
                            </p>
                            ${deleteFormHtml}
                        `;

                        const hr = document.createElement('hr');
                        hr.classList.add('my-4');
                        postContainer.appendChild(postDiv);
                        postContainer.appendChild(hr);
                    });
                    visibleCount += nextPosts.length;
                    if (visibleCount >= allPosts.length) {
                        prevPostsButton.style.display = 'none';
                    }
                    attachDeleteListeners();
                }
            });
            attachDeleteListeners();
        }


        /* index.html: when delete_sign clicked, show the hidden form to input SecretKey */
        const deleteLinks = document.querySelectorAll('.delete-post');
        deleteLinks.forEach(link => {
            link.addEventListener('click', function(event) {
                event.preventDefault();
                const postId = this.dataset.postId;
                const deleteForm = document.getElementById('deleteForm' + postId);
                if (deleteForm) {
                    deleteForm.style.display = 'block';
                    // Update form action here
                    deleteForm.action = `/delete-post/${postId}`;
                }
            });
        });
    }


    /* post.html: Show Add_Comment textarea */
    if (window.location.pathname.match(/^\/post\/\d+$/)) {
        const commentLinks = document.querySelectorAll('.add-comment');
        commentLinks.forEach(link => {
            link.addEventListener('click', function(event) {
                event.preventDefault();
                const postId = this.dataset.postId;
                const commentForm = document.getElementById('commentForm' + postId);
                if (commentForm) {
                    commentForm.style.display = 'block';
                }
            });
        });
    }
});
