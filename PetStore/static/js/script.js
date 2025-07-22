(function($) {

    "use strict";

    // Helper function to initialize preloader
   var initPreloader = function() {
    $(document).ready(function($) {
      var Body = $('body');
      Body.addClass('preloader-site');
    });
    // CHANGED: Use .on('load') instead of .load() for modern jQuery
    $(window).on('load', function() {
      $('.preloader-wrapper').fadeOut();
      $('body').removeClass('preloader-site');
    });
  }
    // Initialize Chocolat light box
    // Uses jQuery to select elements, then gets native DOM elements for Chocolat
    var initChocolat = function() {
        Chocolat($('.image-link').get(), { // .get() converts jQuery object to array of native DOM elements
            imageSize: 'contain',
            loop: true,
        });
    };

    // Initialize Swiper sliders
    // Swiper.js is a standalone library and is initialized with `new Swiper()`,
    // passing a native DOM element or selector string.
    var initSwiper = function() {
        // Swiper slider home 2
        $('.slideshow').each(function() {
            var space = $(this).attr('data-space') ? parseInt($(this).attr('data-space')) : 0;
            var col = $(this).attr('data-col');
            if (typeof col == "undefined" || !col) {
                col = 1;
            }

            var swiper = new Swiper(this, { // Pass 'this' (native DOM element) to Swiper
                slidesPerView: parseInt(col), // Ensure col is parsed as int
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

        // product single page
        var thumb_slider = new Swiper(".product-thumbnail-slider", {
            slidesPerView: 5,
            spaceBetween: 20,
            // autoplay: true,
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
            // autoplay: true,
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

    // Animate Texts
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

    // Input spinner
   var initProductQty = function() {
        $('.product-qty').each(function() {
            var $el_product = $(this);
            // Using .off().on() to prevent multiple bindings if initProductQty is called multiple times
            $el_product.find('.quantity-right-plus').off('click').on('click', function(e) {
                e.preventDefault();
                var $input = $el_product.find('.quantity');
                var currentQuantity = parseInt($input.val());
                var maxQuantity = parseInt($input.attr('max')); // Get max from the input's max attribute

                if (currentQuantity < maxQuantity) {
                    $input.val(currentQuantity + 1);
                }
            });

            $el_product.find('.quantity-left-minus').off('click').on('click', function(e) {
                e.preventDefault();
                var $input = $el_product.find('.quantity');
                var currentQuantity = parseInt($input.val());
                var minQuantity = parseInt($input.attr('min')); // Get min from the input's min attribute

                if (currentQuantity > minQuantity) {
                    $input.val(currentQuantity - 1);
                }
            });

            // Optional: Add change listener for direct input into the textbox
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

    // Initialize jarallax parallax
    // Uses jQuery to select elements, then gets native DOM elements for jarallax
    var initJarallax = function() {
        jarallax($(".jarallax").get()); // .get() converts jQuery object to array of native DOM elements

        jarallax($(".jarallax-keep-img").get(), {
            keepImg: true,
        });
    };

    // Modal Quick View functionality
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
        // Use event delegation on the modal itself, as its content is dynamic
        // This ensures the event listeners work even after new content is loaded
        $('#productQuickViewModal').on('click', '.quantity-right-plus', function(e) {
            e.preventDefault();
            var $input = $(this).closest('.product-qty').find('.quantity');
            var currentQuantity = parseInt($input.val());
            var maxQuantity = parseInt($input.attr('max')); // Get max from the input's max attribute

            if (currentQuantity < maxQuantity) {
                $input.val(currentQuantity + 1);
            }
        });

        $('#productQuickViewModal').on('click', '.quantity-left-minus', function(e) {
            e.preventDefault();
            var $input = $(this).closest('.product-qty').find('.quantity');
            var currentQuantity = parseInt($input.val());
            var minQuantity = parseInt($input.attr('min')); // Get min from the input's min attribute

            if (currentQuantity > minQuantity) {
                $input.val(currentQuantity - 1);
            }
        });

        // Optional: Add change listener for direct input into the textbox within the modal
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

      // Function to get CSRF token from cookie
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Function to update the global cart item count (e.g., in header)
    var updateCartCount = function(count) {
        $('#cart-item-count').text(count);
        if (count > 0) {
            $('#cart-item-count').removeClass('d-none'); // Show badge if items exist
        } else {
            $('#cart-item-count').addClass('d-none'); // Hide badge if no items
        }
    };

    
    var fetchAndRenderCartDetails = function() {
        const $cartDialogContent = $('#cart-dialog-content');
        const $cartDialogTotalPrice = $('#cart-dialog-total-price');
        const $cartTotalItemsCount = $('.cart-total-items-count'); // Assuming you have an element for this
        const $cartDialogCheckoutBtn = $('#cart-dialog-checkout-btn'); // Assuming you have a checkout button

        $cartDialogContent.html('<p class="text-center text-muted">Loading cart...</p>'); // Show loading state

        $.ajax({
            // IMPORTANT: Use Django's URL reversing for robustness
            url: '/api/cart/', // Correct Django URL for cart details
            method: 'GET',
            dataType: 'json',
            success: function(response) {
                console.log(response); // Keep this for debugging

                let cartHtml = '';
                if (response.cart_items && response.cart_items.length > 0) {
                    cartHtml = '<ul class="list-group list-group-flush">';
                    response.cart_items.forEach(item => {
                        // Ensure product image URL is correctly accessed (from serializer)
                        const imageUrl = item.product.image || '/static/images/placeholder.png';
                        // Ensure current_price is correctly accessed and formatted
                        console.log(item.product);
                        const unitPrice = item.product.original_price !== undefined && item.product.original_price !== null
                                        ? parseInt(item.product.discounted_price??item.product.original_price).toFixed(2) : '0.00';
                        // Ensure total_price is correctly accessed and formatted
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
                    $cartDialogCheckoutBtn.removeClass('disabled'); // Enable checkout button
                } else {
                    cartHtml = '<p class="text-center text-muted py-5">Your cart is empty.</p>';
                    $cartDialogCheckoutBtn.addClass('disabled'); // Disable checkout button
                }

                $cartDialogContent.html(cartHtml);
                // Ensure total is formatted to 2 decimal places
                $cartDialogTotalPrice.text(`$${response.total.toFixed(2)}`);
                updateCartCount(response.total_items); // Update global counter
                
            },
            error: function(xhr, status, error) {
                console.error('Error fetching cart details:', status, error, xhr.responseText);
                $cartDialogContent.html('<p class="text-danger text-center py-5">Failed to load cart. Please try again.</p>');
                $cartDialogTotalPrice.text(`$0.00`); // Show 0.00 on error
                updateCartCount(0); // Reset counter on error
            }
        });
    };

    var updateCartItemQuantity = function(productId, change) {
        const $qtyInput = $(`#cart-dialog-content .cart-item-row[data-product-id="${productId}"] input.quantity-display`);
        const currentQuantity = parseInt($qtyInput.val());
        let newQuantity = currentQuantity + change;

        // Special handling for decrementing from 1 to 0 (which means remove)
        if (newQuantity <= 0) {
            if (currentQuantity === 1 && change === -1) { // If going from 1 to 0 by decrement
                removeCartItem(productId); // Remove completely
                return;
            }
            newQuantity = 0; // Prevent negative quantity in input
        }

        // Disable buttons for feedback during AJAX call (optional)
        const $cartItemRow = $(`#cart-dialog-content .cart-item-row[data-product-id="${productId}"]`);
        $cartItemRow.find('button').prop('disabled', true);

        $.ajax({
            url: 'api/cart/update-quantity/', // Django URL
            method: 'POST',
            data: JSON.stringify({ // Send data as JSON
                'product_id': productId,
                'quantity': newQuantity // Send the *absolute new quantity*
            }),
            contentType: 'application/json',
            headers: {
                'X-CSRFToken': getCookie('csrftoken') // IMPORTANT for POST requests
            },
            success: function(response) {
                if (response.success) {
                    fetchAndRenderCartDetails(); // Re-render the cart on success
                    updateCartCount(response.cart_total_items); // Update main cart count display
                } else {
                    alert('Error updating quantity: ' + (response.error || 'An unknown error occurred.'));
                }
            },
            error: function(xhr, status, error) {
                console.error('Update cart quantity error:', status, error, xhr.responseText);
                alert('Failed to update cart quantity. Please try again.');
            },
            complete: function() {
                $cartItemRow.find('button').prop('disabled', false); // Re-enable buttons
            }
        });
    };

    var removeCartItem = function(productId) {
        if (!confirm('Are you sure you want to remove this item from your cart?')) {
            return;
        }

        const $cartItemRow = $(`#cart-dialog-content .cart-item-row[data-product-id="${productId}"]`);
        $cartItemRow.find('button').prop('disabled', true).text('Removing...'); // Disable and change text

        $.ajax({
            url: 'api/cart/remove/', // Django URL
            method: 'POST',
            data: JSON.stringify({
                'product_id': productId
            }),
            contentType: 'application/json',
            headers: {
                'X-CSRFToken': getCookie('csrftoken') // IMPORTANT
            },
            success: function(response) {
                if (response.success) {
                    fetchAndRenderCartDetails(); // Re-render the cart on success
                    updateCartCount(response.cart_total_items); // Update main cart count display
                } else {
                    alert('Error removing item: ' + (response.error || 'An unknown error occurred.'));
                }
            },
            error: function(xhr, status, error) {
                console.error('Remove cart item error:', status, error, xhr.responseText);
                alert('Failed to remove item from cart. Please try again.');
            }
            // 'complete' not needed here as fetchAndRenderCartDetails will rebuild the HTML
        });
    };


    var initCartItemControls = function() {
        // Decrement quantity button (-)
        $(document).on('click', '.decrement-qty-btn', function() {
            const productId = $(this).data('product-id');
            updateCartItemQuantity(productId, -1); // Call the update function with change -1
        });

        // Increment quantity button (+)
        $(document).on('click', '.increment-qty-btn', function() {
            const productId = $(this).data('product-id');
            updateCartItemQuantity(productId, 1); // Call the update function with change +1
        });

        // Remove item button
        $(document).on('click', '.remove-from-cart-btn', function() {
            const productId = $(this).data('product-id');
            removeCartItem(productId); // Call the remove function
        });
    };

    // Handle 'Add to Cart' button clicks (event delegation for dynamic buttons)
    var initAddToCart = function() {
        $(document).on('click', '.btn-cart', function(e) {
            e.preventDefault();
            const $button = $(this);
            const productId = $button.data('product-id');
            // Check if the button is within a modal product view or main grid
            let quantity = 1; // Default quantity
            let $quantityInput = $button.closest('.button-area').find('.quantity');

            if ($quantityInput.length) {
                quantity = parseInt($quantityInput.val());
            }

            if (productId && quantity >= 1) {
                // Disable button and show loading state
                $button.prop('disabled', true).text('Adding...');

                $.ajax({
                    url: 'api/cart/add/', // Your Django URL for add to cart
                    method: 'POST',
                    data: JSON.stringify({
                        'product_id': productId,
                        'quantity': quantity
                    }),
                    contentType: 'application/json',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken') // Include CSRF token
                    },
                    success: function(response) {
                        if (response.success) {
                            alert(response.message); // Or use a nicer notification system
                            updateCartCount(response.cart_total_items);

                            // Optional: Close quick view modal if open
                            $('#productQuickViewModal').modal('hide');

                            // Open and refresh the cart dialog after adding
                            var cartDialog = new bootstrap.Modal(document.getElementById('cartDialogModal'));
                            cartDialog.show();
                            fetchAndRenderCartDetails(); // Refresh cart content

                        } else {
                            alert('Error: ' + response.error);
                        }
                    },
                    error: function(xhr, status, error) {
                        console.error('Add to cart error:', status, error, xhr.responseText);
                        alert('Failed to add item to cart. Please try again.');
                    },
                    complete: function() {
                        // Re-enable button
                        $button.prop('disabled', false).html('Add to Cart');
                    }
                });
            } else {
                alert('Invalid product ID or quantity.');
            }
        });

        // Event listener for when the cart dialog is shown
        $('#cartDialogModal').on('show.bs.modal', function() {
            fetchAndRenderCartDetails(); // Load cart content every time modal is opened
        });
    };


    var fetchAndRenderProducts = function() {
        const $productListContainer = $('#product-list-container');
        // Display a loading message while fetching data
        $productListContainer.html('<p class="text-center text-muted py-5">Loading products...</p>');

        // Make an AJAX request to your Django API endpoint for products
        $.ajax({
            url: '/api/products/', // Make sure this URL is correctly configured in Django's urls.py
            method: 'GET',
            dataType: 'json', // Expect a JSON response
            success: function(response) {
                // Check if the response contains products and if there are any
                if (response && response.length > 0) {
                    $productListContainer.empty(); // Clear the loading message

                    // Loop through each product in the response
                    response.forEach(function(product) {
                        // Construct the HTML for each product using template literals
                        // Ensure that product properties (like product.id, product.name, etc.)
                        // match the keys in the JSON response from your Django API.
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
                                            ${product.discounted_price !== null ? // Check if discounted_price exists
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
                                                    ${product.stock > 0 ? // Check if product is in stock
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
                        initProductQty(); // Reinitialize quantity controls for new products
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

    // Document ready block (all initializations should go here)
    $(document).ready(function() {
        initPreloader();
        initTextFx();
        initSwiper();
        initJarallax();
        initChocolat();
        initProductQuickViewModal(); // Initialize the modal quick view
        initModalProductQty(); 
        initAddToCart(); 
        fetchAndRenderCartDetails();
        fetchAndRenderProducts();
        initCartItemControls(); 
    });

})(jQuery);