(function($) {

    "use strict";

   var initPreloader = function() {
    $(document).ready(function($) {
      var Body = $('body');
      Body.addClass('preloader-site');
    });
    
      $('.preloader-wrapper').fadeOut();
    $(window).on('load', function() {
      $('body').removeClass('preloader-site');
    });
  }
    var initChocolat = function() {
        Chocolat($('.image-link').get(), { 
            imageSize: 'contain',
            loop: true,
        });
    };

    var initSwiper = function() {
        $('.slideshow').each(function() {
            var space = $(this).attr('data-space') ? parseInt($(this).attr('data-space')) : 0;
            var col = $(this).attr('data-col');
            if (typeof col == "undefined" || !col) {
                col = 1;
            }

            var swiper = new Swiper(this, { 
                slidesPerView: parseInt(col), 
                spaceBetween: space,
                speed: 1000,
                loop: true,
                pagination: {
                    el: ".slideshow-swiper-pagination",
                    clickable: true,
                },
            });
        });

        var testimonialSwiper = new Swiper(".testimonial-swiper", {
            slidesPerView: 1,
            spaceBetween: 20,
            navigation: {
                nextEl: ".testimonial-button-next",
                prevEl: ".testimonial-button-prev",
            },
        });

        var brand_swiper = new Swiper(".brand-carousel", {
            slidesPerView: 4,
            spaceBetween: 30,
            speed: 500,
            navigation: {
                nextEl: ".brand-carousel-next",
                prevEl: ".brand-carousel-prev",
            },
            breakpoints: {
                0: {
                    slidesPerView: 2,
                },
                768: {
                    slidesPerView: 2,
                },
                991: {
                    slidesPerView: 3,
                },
                1500: {
                    slidesPerView: 4,
                },
            }
        });

        var productSwiper = new Swiper(".product-swiper", {
            spaceBetween: 20,
            pagination: {
                el: ".product-swiper-pagination",
                clickable: true,
            },
            breakpoints: {
                0: {
                    slidesPerView: 1,
                },
                660: {
                    slidesPerView: 3,
                },
                980: {
                    slidesPerView: 4,
                },
                1500: {
                    slidesPerView: 5,
                }
            },
        });

        var products_swiper = new Swiper(".products-carousel", {
            slidesPerView: 5,
            spaceBetween: 30,
            speed: 500,
            navigation: {
                nextEl: ".products-carousel-next",
                prevEl: ".products-carousel-prev",
            },
            breakpoints: {
                0: {
                    slidesPerView: 1,
                },
                768: {
                    slidesPerView: 3,
                },
                991: {
                    slidesPerView: 4,
                },
                1500: {
                    slidesPerView: 5,
                },
            }
        });

        var thumb_slider = new Swiper(".product-thumbnail-slider", {
            slidesPerView: 5,
            spaceBetween: 20,
            direction: "vertical",
            breakpoints: {
                0: {
                    direction: "horizontal"
                },
                992: {
                    direction: "vertical"
                },
            },
        });

        var large_slider = new Swiper(".product-large-slider", {
            slidesPerView: 1,
            spaceBetween: 0,
            effect: 'fade',
            thumbs: {
                swiper: thumb_slider,
            },
            pagination: {
                el: ".swiper-pagination",
                clickable: true,
            },
        });
    };

    var initTextFx = function() {
        $('.txt-fx').each(function() {
            var newstr = '';
            var count = 0;
            var delay = 100;
            var stagger = 10;
            var words = this.textContent.split(/\s/);
            var arrWords = new Array();

            $.each(words, function(key, value) {
                newstr = '<span class="word">';

                for (var i = 0, l = value.length; i < l; i++) {
                    newstr += "<span class='letter' style='transition-delay:" + (delay + stagger * count) + "ms;'>" + value[i] + "</span>";
                    count++;
                }
                newstr += '</span>';

                arrWords.push(newstr);
                count++;
            });

            this.innerHTML = arrWords.join("<span class='letter' style='transition-delay:" + delay + "ms;'>&nbsp;</span>");
        });
    };

   var initProductQty = function() {
        $('.product-qty').each(function() {
            var $el_product = $(this);
            $el_product.find('.quantity-right-plus').off('click').on('click', function(e) {
                e.preventDefault();
                var $input = $el_product.find('.quantity');
                var currentQuantity = parseInt($input.val());
                var maxQuantity = parseInt($input.attr('max')); 

                if (currentQuantity < maxQuantity) {
                    $input.val(currentQuantity + 1);
                }
            });

            $el_product.find('.quantity-left-minus').off('click').on('click', function(e) {
                e.preventDefault();
                var $input = $el_product.find('.quantity');
                var currentQuantity = parseInt($input.val());
                var minQuantity = parseInt($input.attr('min')); 

                if (currentQuantity > minQuantity) {
                    $input.val(currentQuantity - 1);
                }
            });

            $el_product.find('.quantity').off('change').on('change', function() {
                var $input = $(this);
                var value = parseInt($input.val());
                var min = parseInt($input.attr('min'));
                var max = parseInt($input.attr('max'));

                if (isNaN(value) || value < min) {
                    $input.val(min);
                } else if (value > max) {
                    $input.val(max);
                }
            });
        });
    };

    var initJarallax = function() {
        jarallax($(".jarallax").get()); 

        jarallax($(".jarallax-keep-img").get(), {
            keepImg: true,
        });
    };

    var initProductQuickViewModal = function() {
        const $productQuickViewModal = $('#productQuickViewModal');
        const $modalProductContent = $('#modalProductContent');

        $productQuickViewModal.on('show.bs.modal', function(event) {
            const $button = $(event.relatedTarget);
            const productId = $button.data('product-id');
            $modalProductContent.html('<p>Loading product information...</p>');

            if (productId) {
                const fetchUrl = `/product-quick-view/${productId}/`;

                $.ajax({
                    url: fetchUrl,
                    method: 'GET',
                    dataType: 'html',
                    success: function(responseHtml) {
                        $modalProductContent.html(responseHtml);
                    },
                    error: function(xhr, status, error) {
                        console.error('Error fetching product details:', status, error);
                        $modalProductContent.html('<p class="text-danger">Failed to load product details. Please try again.</p>');
                    }
                });
            }
        });
    };

     var initModalProductQty = function() {
        $('#productQuickViewModal').on('click', '.quantity-right-plus', function(e) {
            e.preventDefault();
            var $input = $(this).closest('.product-qty').find('.quantity');
            var currentQuantity = parseInt($input.val());
            var maxQuantity = parseInt($input.attr('max')); 

            if (currentQuantity < maxQuantity) {
                $input.val(currentQuantity + 1);
            }
        });

        $('#productQuickViewModal').on('click', '.quantity-left-minus', function(e) {
            e.preventDefault();
            var $input = $(this).closest('.product-qty').find('.quantity');
            var currentQuantity = parseInt($input.val());
            var minQuantity = parseInt($input.attr('min'));

            if (currentQuantity > minQuantity) {
                $input.val(currentQuantity - 1);
            }
        });

        $('#productQuickViewModal').on('change', '.quantity', function() {
            var $input = $(this);
            var value = parseInt($input.val());
            var min = parseInt($input.attr('min'));
            var max = parseInt($input.attr('max'));

            if (isNaN(value) || value < min) {
                $input.val(min);
            } else if (value > max) {
                $input.val(max);
            }
        });
    };

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    var updateCartCount = function(count) {
        $('#cart-item-count').text(count);
        if (count > 0) {
            $('#cart-item-count').removeClass('d-none'); 
        } else {
            $('#cart-item-count').addClass('d-none'); 
        }
    };

    
    var fetchAndRenderCartDetails = function() {
        const $cartDialogContent = $('#cart-dialog-content');
        const $cartDialogTotalPrice = $('#cart-dialog-total-price');
        const $cartTotalItemsCount = $('.cart-total-items-count'); 
        const $cartDialogCheckoutBtn = $('#cart-dialog-checkout-btn'); 

        $cartDialogContent.html('<p class="text-center text-muted">Loading cart...</p>'); 

        $.ajax({
            url: '/api/cart/', 
            method: 'GET',
            dataType: 'json',
            success: function(response) {
                console.log(response); 

                let cartHtml = '';
                if (response.cart_items && response.cart_items.length > 0) {
                    cartHtml = '<ul class="list-group list-group-flush">';
                    response.cart_items.forEach(item => {
                        const imageUrl = item.product.image || '/static/images/placeholder.png';
                        console.log(item.product);
                        const unitPrice = item.product.original_price !== undefined && item.product.original_price !== null
                                        ? parseInt(item.product.discounted_price??item.product.original_price).toFixed(2) : '0.00';
                        const itemTotalPrice = item.total_price !== undefined && item.total_price !== null
                                            ? item.total_price.toFixed(2) : '0.00';

                        cartHtml += `
                            <li class="list-group-item d-flex justify-content-between align-items-center cart-item-row" data-product-id="${item.product.id}">
                                <div class="d-flex align-items-center">
                                    <img src="${imageUrl}" alt="${item.product.name}" class="img-thumbnail me-3" style="width: 60px; height: 60px; object-fit: cover;">
                                    <div>
                                        <h6 class="my-0">${item.product.name}</h6>
                                        <div class="d-flex align-items-center mt-1">
                                            <small class="text-muted me-2">Qty:</small>
                                            <div class="input-group input-group-sm" style="width: 100px;">
                                                <button class="btn btn-outline-secondary decrement-qty-btn" type="button" data-product-id="${item.product.id}">-</button>
                                                <input type="text" class="form-control text-center quantity-display" value="${item.quantity}" readonly>
                                                <button class="btn btn-outline-secondary increment-qty-btn" type="button" data-product-id="${item.product.id}">+</button>
                                            </div>
                                        </div>
                                        <small class="text-muted">Unit Price: $${unitPrice}</small>
                                    </div>
                                </div>
                                <div class="d-flex flex-column align-items-end">
                                    <span class="fw-bold mb-2">$${itemTotalPrice}</span>
                                    <button type="button" class="btn btn-danger btn-sm remove-from-cart-btn" data-product-id="${item.product.id}">
                                        Remove
                                    </button>
                                </div>
                            </li>
                        `;
                    });
                    cartHtml += '</ul>';
                    $cartDialogCheckoutBtn.removeClass('disabled'); 
                } else {
                    cartHtml = '<p class="text-center text-muted py-5">Your cart is empty.</p>';
                    $cartDialogCheckoutBtn.addClass('disabled'); 
                }

                $cartDialogContent.html(cartHtml);
                $cartDialogTotalPrice.text(`$${response.total.toFixed(2)}`);
                updateCartCount(response.total_items);
                
            },
            error: function(xhr, status, error) {
                console.error('Error fetching cart details:', status, error, xhr.responseText);
                $cartDialogContent.html('<p class="text-danger text-center py-5">Failed to load cart. Please try again.</p>');
                $cartDialogTotalPrice.text(`$0.00`); 
                updateCartCount(0); 
            }
        });
    };

    var updateCartItemQuantity = function(productId, change) {
        const $qtyInput = $(`#cart-dialog-content .cart-item-row[data-product-id="${productId}"] input.quantity-display`);
        const currentQuantity = parseInt($qtyInput.val());
        let newQuantity = currentQuantity + change;

        if (newQuantity <= 0) {
            if (currentQuantity === 1 && change === -1) { 
                removeCartItem(productId); 
                return;
            }
            newQuantity = 0; 
        }

        const $cartItemRow = $(`#cart-dialog-content .cart-item-row[data-product-id="${productId}"]`);
        $cartItemRow.find('button').prop('disabled', true);

        $.ajax({
            url: 'api/cart/update-quantity/', 
            method: 'POST',
            data: JSON.stringify({ 
                'product_id': productId,
                'quantity': newQuantity 
            }),
            contentType: 'application/json',
            headers: {
                'X-CSRFToken': getCookie('csrftoken') 
            },
            success: function(response) {
                if (response.success) {
                    fetchAndRenderCartDetails();
                    updateCartCount(response.cart_total_items); 
                } else {
                    alert('Error updating quantity: ' + (response.error || 'An unknown error occurred.'));
                }
            },
            error: function(xhr, status, error) {
                console.error('Update cart quantity error:', status, error, xhr.responseText);
                alert('Failed to update cart quantity. Please try again.');
            },
            complete: function() {
                $cartItemRow.find('button').prop('disabled', false); 
            }
        });
    };

    var removeCartItem = function(productId) {
        if (!confirm('Are you sure you want to remove this item from your cart?')) {
            return;
        }

        const $cartItemRow = $(`#cart-dialog-content .cart-item-row[data-product-id="${productId}"]`);
        $cartItemRow.find('button').prop('disabled', true).text('Removing...'); 

        $.ajax({
            url: 'api/cart/remove/', 
            method: 'POST',
            data: JSON.stringify({
                'product_id': productId
            }),
            contentType: 'application/json',
            headers: {
                'X-CSRFToken': getCookie('csrftoken') 
            },
            success: function(response) {
                if (response.success) {
                    fetchAndRenderCartDetails(); 
                    updateCartCount(response.cart_total_items); 
                } else {
                    alert('Error removing item: ' + (response.error || 'An unknown error occurred.'));
                }
            },
            error: function(xhr, status, error) {
                console.error('Remove cart item error:', status, error, xhr.responseText);
                alert('Failed to remove item from cart. Please try again.');
            }
        });
    };


    var initCartItemControls = function() {
        $(document).on('click', '.decrement-qty-btn', function() {
            const productId = $(this).data('product-id');
            updateCartItemQuantity(productId, -1); 
        });

        $(document).on('click', '.increment-qty-btn', function() {
            const productId = $(this).data('product-id');
            updateCartItemQuantity(productId, 1); 
        });

        $(document).on('click', '.remove-from-cart-btn', function() {
            const productId = $(this).data('product-id');
            removeCartItem(productId); 
        });
    };

    var initAddToCart = function() {
        $(document).on('click', '.btn-cart', function(e) {
            e.preventDefault();
            const $button = $(this);
            const productId = $button.data('product-id');
            let quantity = 1; 
            let $quantityInput = $button.closest('.button-area').find('.quantity');

            if ($quantityInput.length) {
                quantity = parseInt($quantityInput.val());
            }

            if (productId && quantity >= 1) {
                $button.prop('disabled', true).text('Adding...');

                $.ajax({
                    url: '/api/cart/add/', 
                    method: 'POST',
                    data: JSON.stringify({
                        'product_id': productId,
                        'quantity': quantity
                    }),
                    contentType: 'application/json',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken') 
                    },
                    success: function(response) {
                        if (response.success) {
                            updateCartCount(response.cart_total_items);

                            $('#productQuickViewModal').modal('hide');

                            var cartDialog = new bootstrap.Modal(document.getElementById('cartDialogModal'));
                            cartDialog.show();
                            fetchAndRenderCartDetails(); 

                        } else {
                            alert('Error: ' + response.error);
                        }
                    },
                    error: function(xhr, status, error) {
                        console.error('Add to cart error:', status, error, xhr.responseText);
                        alert('Failed to add item to cart. Please try again.');
                    },
                    complete: function() {
                        $button.prop('disabled', false).html('Add to Cart');
                    }
                });
            } else {
                alert('Invalid product ID or quantity.');
            }
        });

        $('#cartDialogModal').on('show.bs.modal', function() {
            fetchAndRenderCartDetails(); 
        });
    };

    let mySwiper = null;

    function loadFeedbackSwiper() {
        const swiperWrapper = $('#swiper-wrapper-content');
        const feedbackLoadingIndicator = $('#feedback-loading-indicator');
        const noFeedbackMessage = $('#no-feedback-message');
        const feedbackLoadError = $('#feedback-load-error');
        const feedbackSwiper = $('#feedbackSwiper'); 

        feedbackLoadingIndicator.removeClass('d-none');
        swiperWrapper.empty(); 
        noFeedbackMessage.addClass('d-none');
        feedbackLoadError.addClass('d-none');
        feedbackSwiper.addClass('d-none'); 
        if (mySwiper) {
            mySwiper.destroy(true, true); 
            mySwiper = null;
        }

        $.ajax({
            url: "/api/feedback/", 
            type: 'GET',
            success: function(data) {
                feedbackLoadingIndicator.addClass('d-none'); 

                if (data.length === 0) {
                    noFeedbackMessage.removeClass('d-none'); 
                    return; 
                }

                data.forEach(feedback => {
                    const imagesHtml = feedback.images.map(img => `
                        <img src="${img.image}" class="img-fluid rounded me-2 mb-2" alt="Feedback Image" style="max-height: 100px; object-fit: cover;">
                    `).join('');

                    const swiperSlide = `
                        <div class="swiper-slide">
                            <div class="card position-relative text-left p-5 border-light shadow-sm rounded-3 h-100 d-flex flex-column">
                                <blockquote>"${feedback.message}"</blockquote>
                                <h5 class="mt-auto fw-normal">${feedback.user_display}</h5>
                                ${feedback.email ? `<div class="text-muted small">${feedback.email}</div>` : ''}
                                <div class="text-muted small">${new Date(feedback.submitted_at).toLocaleDateString()}</div>
                                ${imagesHtml ? `<div class="mt-3 image-preview-container">${imagesHtml}</div>` : ''}
                            </div>
                        </div>
                    `;
                    swiperWrapper.append(swiperSlide); 
                });

                feedbackSwiper.removeClass('d-none'); 

        mySwiper = new Swiper('#feedbackSwiper', {
                slidesPerView: 1,
                spaceBetween: 30,
                loop: true,

                autoHeight: true, 

                pagination: {
                    el: '.swiper-pagination',
                    clickable: true,
                },

                navigation: {
                    nextEl: '.swiper-button-next',
                    prevEl: '.swiper-button-prev',
                },

                autoplay: {
                    delay: 5000,
                    disableOnInteraction: false,
                },
            });
            },
            error: function(xhr, status, error) {
                console.error('Error loading feedback:', xhr.responseText);
                feedbackLoadingIndicator.addClass('d-none'); 
                feedbackLoadError.removeClass('d-none');
            }
        });
    }
    var fetchAndRenderProducts = function() {
        const $productListContainer = $('#product-list-container');
        $productListContainer.html('<p class="text-center text-muted py-5">Loading products...</p>');

        $.ajax({
            url: '/api/products/',
            method: 'GET',
            dataType: 'json',
            success: function(response) {
                if (response && response.length > 0) {
                    $productListContainer.empty(); 

                    var item = 0;
                    response.forEach(function(product) {
                        if (item>=8)return;
                        const productHtml = `
                            <div class="col">
                                <div class="product-item mb-4">
                                    <figure>
                                        <a href="#" class="open-product-modal" data-bs-toggle="modal" data-bs-target="#productQuickViewModal" data-product-id="${product.id}" title="${product.name}">
                                            <img src="${product.image}" alt="${product.name}" class="tab-image img-fluid rounded-3">
                                        </a>
                                    </figure>
                                    <div class="d-flex flex-column text-center">
                                        <h3 class="fs-5 fw-normal">
                                            <a href="#" class="text-decoration-none open-product-modal" data-bs-toggle="modal" data-bs-target="#productQuickViewModal" data-product-id="${product.id}">${product.name}</a>
                                        </h3>
                                        <div class="d-flex justify-content-center align-items-center gap-2">
                                            ${product.discounted_price !== null ? 
                                                `<del>$${product.original_price}</del>
                                                <span class="text-dark fw-semibold">$${product.discounted_price}</span>` :
                                                `<span class="text-dark fw-semibold">$${product.original_price}</span>`
                                            }
                                        </div>
                                        <div class="button-area p-3">
                                            <div class="justify-content-center d-flex mb-3">
                                                <div class="input-group product-qty col-8 col-lg-6" style="width: 100px; display: flex; align-items: center; gap: 5px;">
                                                    <span class="input-group-btn">
                                                        <button type="button" class="quantity-left-minus btn btn-light btn-number" data-type="minus" data-field="quantity-${product.id}">
                                                            <svg width="16" height="16"><use xlink:href="#minus"></use></svg>
                                                        </button>
                                                    </span>
                                                    ${product.stock > 0 ? 
                                                        `<input type="text" id="quantity-${product.id}" name="quantity" class="quantity form-control input-number text-center" value="1" min="1" max="${product.stock}">` :
                                                        `<input type="text" id="quantity-${product.id}" name="quantity" class="quantity form-control input-number text-center" value="0" min="0" max="${product.stock}" disabled>` // Disable if out of stock
                                                    }
                                                    <span class="input-group-btn">
                                                        <button type="button" class="quantity-right-plus btn btn-light btn-number" data-type="plus" data-field="quantity-${product.id}">
                                                            <svg width="16" height="16"><use xlink:href="#plus"></use></svg>
                                                        </button>
                                                    </span>
                                                </div>
                                            </div>
                                            <div>
                                                ${product.stock > 0 ?
                                                    `<a href="#" class="btn btn-primary rounded-1 p-2 fs-7 btn-cart" data-product-id="${product.id}">
                                                        Add to Cart
                                                    </a>` :
                                                    `<button type="button" class="btn btn-secondary rounded-1 p-2 fs-7" disabled>Out of Stock</button>`
                                                }
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        `;
                        $productListContainer.append(productHtml);
                        initProductQty();
                        item++ 
                    });
                } else {
                    $productListContainer.html('<div class="col-12 text-center py-5"><p>No products found.</p></div>');
                }
            },
            error: function(xhr, status, error) {
                console.error("Error fetching products:", status, error, xhr.responseText);
                $productListContainer.html('<div class="col-12 text-center py-5"><p>Error loading products. Please try again later.</p></div>');
            }
        });
    };


    var fetchAndRenderLatestProducts = function() {
        const $productListContainer = $('#product-order-by-date');
        $productListContainer.html('<p class="text-center text-muted py-5">Loading products...</p>');

        $.ajax({
            url: '/api/products/filter/', 
            method: 'GET',
            dataType: 'json', 
            success: function(response) {
                if (response && response.length > 0) {
                    $productListContainer.empty(); 

                    var item = 0; 
                    response.forEach(function(product) {
                        if(item >= 4) return; 
                        const productHtml = `
                            <div class="col-xl-3 col-lg-3 col-md-6 col-sm-6 col-6">
                                <div class="product-item mb-4">
                                    <figure style="display: flex; justify-content: center;">
                                        <a href="#" class="open-product-modal" data-bs-toggle="modal" data-bs-target="#productQuickViewModal" data-product-id="${product.id}" title="${product.name}">
                                            <img src="${product.image}" alt="${product.name}" class="tab-image img-fluid rounded-3">
                                        </a>
                                    </figure>
                                    <div class="d-flex flex-column text-center">
                                        <h3 class="fs-5 fw-normal">
                                            <a href="#" class="text-decoration-none open-product-modal" data-bs-toggle="modal" data-bs-target="#productQuickViewModal" data-product-id="${product.id}">${product.name}</a>
                                        </h3>
                                        <div class="d-flex justify-content-center align-items-center gap-2">
                                            ${product.discounted_price !== null ? 
                                                `<del>$${product.original_price}</del>
                                                <span class="text-dark fw-semibold">$${product.discounted_price}</span>` :
                                                `<span class="text-dark fw-semibold">$${product.original_price}</span>`
                                            }
                                        </div>
                                        <div class="button-area p-3">
                                            <div class="justify-content-center d-flex mb-3">
                                                <div class="input-group product-qty col-8 col-lg-6" style="width: 100px; display: flex; align-items: center; gap: 5px;">
                                                    <span class="input-group-btn">
                                                        <button type="button" class="quantity-left-minus btn btn-light btn-number" data-type="minus" data-field="quantity-${product.id}">
                                                            <svg width="16" height="16"><use xlink:href="#minus"></use></svg>
                                                        </button>
                                                    </span>
                                                    ${product.stock > 0 ? 
                                                        `<input type="text" id="quantity-${product.id}" name="quantity" class="quantity form-control input-number text-center" value="1" min="1" max="${product.stock}">` :
                                                        `<input type="text" id="quantity-${product.id}" name="quantity" class="quantity form-control input-number text-center" value="0" min="0" max="${product.stock}" disabled>` // Disable if out of stock
                                                    }
                                                    <span class="input-group-btn">
                                                        <button type="button" class="quantity-right-plus btn btn-light btn-number" data-type="plus" data-field="quantity-${product.id}">
                                                            <svg width="16" height="16"><use xlink:href="#plus"></use></svg>
                                                        </button>
                                                    </span>
                                                </div>
                                            </div>
                                            <div>
                                                ${product.stock > 0 ?
                                                    `<a href="#" class="btn btn-primary rounded-1 p-2 fs-7 btn-cart" data-product-id="${product.id}">
                                                        Add to Cart
                                                    </a>` :
                                                    `<button type="button" class="btn btn-secondary rounded-1 p-2 fs-7" disabled>Out of Stock</button>`
                                                }
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        `;
                        $productListContainer.append(productHtml);
                        initProductQty(); 
                        item++;
                    });
                } else {
                    $productListContainer.html('<div class="col-12 text-center py-5"><p>No products found.</p></div>');
                }
            },
            error: function(xhr, status, error) {
                console.error("Error fetching products:", status, error, xhr.responseText);
                $productListContainer.html('<div class="col-12 text-center py-5"><p>Error loading products. Please try again later.</p></div>');
            }
        });
    };

    function loadRecentBlogPosts() {
        console.log('Loading recent blog posts...'); 
        const container = $('#recent-blog-posts-container');
        const loadingIndicator = $('#blog-loading-indicator');
        const noPostsMessage = $('#no-blog-posts-message');
        const loadError = $('#blog-load-error');

        loadingIndicator.removeClass('d-none');
        container.empty(); 
        noPostsMessage.addClass('d-none');
        loadError.addClass('d-none');

        $.ajax({
            url: `/api/posts/recent/`,
            type: 'GET',
            dataType: 'json', 
            success: function(data) {
                loadingIndicator.addClass('d-none'); 

                if (data.length === 0) {
                    noPostsMessage.removeClass('d-none'); 
                    return;
                }
                var item = 0
                data.forEach(post => {
                    if(item >= 3) return; 
                    const publishedDate = new Date(post.published_date).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric'
                    });

                    const imageUrl = post.image ? post.image : "{% static 'img/default_blog_image.jpg' %}";
                    const categoryName = post.category ? post.category.name.toUpperCase() : 'UNCATEGORIZED';

                    const postHtml = `
                        <div class="col-md-4 mb-4">
                            <div class="card h-100 shadow-sm">
                                <img src="${imageUrl}" class="card-img-top blog-card-img" alt="${post.title}">
                                <div class="card-body">
                                    <p class="card-text text-muted text-uppercase text-xxs mb-1">
                                        ${publishedDate} &bull; ${categoryName}
                                    </p>
                                    <h5 class="card-title">${post.title}</h5>
                                    <p class="card-text text-sm">${post.short_description || 'No description available.'}</p>
                                    <a href="/blog/${post.id}/" class="text-primary text-sm font-weight-bold">
                                        Read More <i class="fas fa-arrow-right ms-1"></i>
                                    </a>
                                </div>
                            </div>
                        </div>
                    `;
                    container.append(postHtml);
                    item++;
                });
            },
            error: function(xhr, status, error) {
                console.error('Error fetching recent blog posts:', xhr.responseText);
                loadingIndicator.addClass('d-none');
                loadError.removeClass('d-none'); 
            }
        });
    }
    $(document).ready(function() {
        initPreloader();
        initTextFx();
        initSwiper();
        initJarallax();
        initChocolat();
        initProductQuickViewModal(); 
        initModalProductQty(); 
        initAddToCart(); 
        fetchAndRenderCartDetails();
        fetchAndRenderProducts();
        initCartItemControls(); 
        loadFeedbackSwiper(); 
        loadRecentBlogPosts();
        fetchAndRenderLatestProducts();
    });

})(jQuery);


$(document).ready(function() {
    const searchInput = $('#search-input');
    const searchOverlay = $('#search-overlay');
    const resultsContainer = $('#search-results-container');
    const closeBtn = $('#close-overlay');
    let timeout = null;

    // Show the overlay
    function showOverlay() {
        searchOverlay.css('width', '100%');
    }

    // Hide the overlay
    function hideOverlay() {
        searchOverlay.css('width', '0%');
    }

    // Event listener for the close button
    closeBtn.on('click', hideOverlay);
    
    // Event listener for the input field
    searchInput.on('input', function() {
        // Clear any previous timeout
        clearTimeout(timeout);

        const query = $(this).val().trim();

        if (query.length > 0) {
            // Wait for a short period before sending the request
            timeout = setTimeout(() => {
                fetchResults(query);
            }, 300);
        } else {
            // If the input is empty, hide the overlay and clear results
            hideOverlay();
            resultsContainer.empty();
        }
    });

    // Function to fetch results from Django view using $.ajax
    function fetchResults(query) {
        // Replace with your Django URL
        const url = '/api/search_products/';

        $.ajax({
            url: url,
            data: {
                'q': query
            },
            dataType: 'json',
            success: function(data) {
                displayResults(data);
                showOverlay();
            },
            error: function(jqXHR, textStatus, errorThrown) {
                console.error('Error fetching search results:', textStatus, errorThrown);
                resultsContainer.html('<p>An error occurred.</p>');
                showOverlay();
            }
        });
    }
    
    // Alternatively, a simpler $.get() call
    /*
    function fetchResults(query) {
        $.get('/search_products/', { q: query }, function(data) {
            displayResults(data);
            showOverlay();
        }).fail(function() {
            console.error('Error fetching search results');
            resultsContainer.html('<p>An error occurred.</p>');
            showOverlay();
        });
    }
    */

    // Function to display the results in the overlay
    function displayResults(products) {
        resultsContainer.empty(); // Clear previous results

        if (products.length === 0) {
            resultsContainer.html('<p>No products found.</p>');
            return;
        }

        const resultsHtml = products.map(product => `
            <div class="search-result-item">
                <h4 style="color:white">${product.name}</h4>
                <p>Price: $${product.price}</p>
                <a href="${product.url}" style="color:cyan">View Details</a>
            </div>
        `).join('');

        resultsContainer.html(resultsHtml);
    }
});